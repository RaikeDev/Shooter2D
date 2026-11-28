import numpy as np
from skin import SUPPORT, RING_KNIVES, SECTION_COUNT, INVERSE, clipped_slice, normals_tris, ease_array
from motion import hips

MARGIN = .026
LEVELS = np.linspace(0, 1, 15)
WAIST = .263
FACING = RING_KNIVES + np.pi / SECTION_COUNT
EDGE_BAND = .062

def clip(triangle, distance):
    vertices = []
    for i, current in enumerate(triangle):
        previous = triangle[i-1]
        a, b = distance[i-1], distance[i]
        if (a >= 0) != (b >= 0):
            vertices.append(previous + (current - previous) * (a / (a - b)))
        if b >= 0:
            vertices.append(current)
    return [point for i in range(1, len(vertices)-1)
            for point in (vertices[0], vertices[i], vertices[i+1])]

def shell(j, parts):
    pelvis = j['pelvis']
    frame = hips(j)
    legs = np.concatenate([(pos - pelvis) @ frame for name, pos, *_ in parts
                           if name.startswith(('thigh.', 'shin.', 'boot-cuff.'))])
    knees = np.array([(j['knee.' + s] - pelvis) @ frame for s in ('L', 'R')])
    crouch = ease_array((2.21 - pelvis[2]) / 1.16)
    front = np.cos(FACING)
    forward = ease_array((front + .64) / 1.44)
    normals = np.column_stack((front, np.sin(FACING)))
    stride = np.zeros(SECTION_COUNT)
    for knee in knees:
        direction = knee[:2] / max(np.linalg.norm(knee[:2]), .01)
        panel = ease_array((normals @ direction - .12) / .63)
        reach = ease_array((knee[0] - .30) / .48)
        height = ease_array((knee[2] + .98) / .39)
        stride = np.maximum(stride, panel * (.16 * reach + .24 * height))
    # The leading panel rises at its own knee. The sides and back continue to hang.
    hem = -.94 + crouch * (.355 + .157 * forward) + (1. - crouch) * stride
    bottom = -.94 + .355 * crouch
    z_levels = WAIST + (bottom - WAIST) * LEVELS
    slab_supports = []
    for lo, hi in zip(z_levels[1:], z_levels[:-1]):
        section = clipped_slice(legs, lo, hi)
        slab_supports.append((section[:, :2] @ SUPPORT.T).max(0) + MARGIN
                             if len(section) else np.full(SECTION_COUNT, -np.inf))
    rings = []
    for i, (z, u) in enumerate(zip(z_levels, LEVELS)):
        # Narrower drape along the rear and sides. The leg envelope always takes precedence.
        rx = .407 + .056 * u - .072 * crouch * u**2
        ry = .565 + .029 * u - .036 * crouch * u
        base = (-.010 + .018 * crouch * u**2) * SUPPORT[:, 0] + np.hypot(rx * SUPPORT[:, 0], ry * SUPPORT[:, 1])
        if i > 0:
            base = np.maximum(base, slab_supports[i-1])
        if i < len(slab_supports):
            base = np.maximum(base, slab_supports[i])
        xy = np.einsum('nij,nj->ni', INVERSE, np.column_stack((base, np.roll(base, -1))))
        rings.append(np.column_stack((xy, np.full(SECTION_COUNT, z))))
    leading_knee = max(knees[:, 0])
    front_limit = max(.52, .31 + .63 * leading_knee) + .90 * crouch
    return np.array(rings), hem, front_limit, frame, pelvis

def make_skirt(j, parts, tag=4):
    rings, hem, front_limit, frame, pelvis = shell(j, parts)
    groups = {0: [], 7: []}
    for i, (top, bottom) in enumerate(zip(rings, rings[1:])):
        for k in range(SECTION_COUNT):
            l = (k + 1) % SECTION_COUNT
            for triangle, limit in (
                (np.array([top[k], bottom[k], top[l]]), hem[[k, k, l]]),
                (np.array([top[l], bottom[k], bottom[l]]), hem[[l, k, l]]),
            ):
                hem_distance = triangle[:, 2] - limit
                front_distance = front_limit - triangle[:, 0] + .18 * (triangle[:, 2] + .55)
                posed_triangles = clip(np.column_stack((triangle, hem_distance)), front_distance)
                for offset in range(0, len(posed_triangles), 3):
                    panel = np.array(posed_triangles[offset:offset+3])
                    d = panel[:, 3]
                    if d.max() <= 0:
                        continue
                    if k in (1, 18) and i >= 2:
                        groups[7].extend(clip(panel[:, :3], d))
                    elif k in (0, 19) or d.min() >= EDGE_BAND:
                        groups[0].extend(clip(panel[:, :3], d))
                    else:
                        groups[0].extend(clip(panel[:, :3], d - EDGE_BAND))
                        band = clip(panel, EDGE_BAND - d)
                        for index in range(0, len(band), 3):
                            V = np.array(band[index:index+3])
                            groups[7].extend(clip(V[:, :3], V[:, 3]))
    meshes = []
    for color, points in groups.items():
        if points:
            posed = np.array(points) @ frame.T + pelvis
            n = normals_tris(posed)
            keep = np.repeat(np.linalg.norm(n[::3], axis=1) > .5, 3)
            meshes.append(('skirt.shell.' + str(color), posed[keep], n[keep], color, tag))
    return meshes
