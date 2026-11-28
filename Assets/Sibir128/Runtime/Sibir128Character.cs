using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Sibir128
{
    [Serializable] public sealed class AtlasPage { public string file; public int width, height; }
    [Serializable] public sealed class AtlasFrame
    {
        public int page, x, y, w, h, pivotX, pivotY, trimX, trimY;
    }
    [Serializable] public sealed class AtlasClip
    {
        public string name; public int phaseCount; public float fps; public bool loop; public int[] frameIds;
    }
    [Serializable] public sealed class AtlasDefinition
    {
        public int schemaVersion, directionCount, canvasWidth, canvasHeight, rootX, rootY;
        public float directionStepDegrees, pixelsPerUnit, pixelsPerB, groundVerticalScale, cycleTravelB;
        public AtlasPage[] pages; public AtlasFrame[] frames; public AtlasClip[] animations;
        public int grabPhase;
        public Vector2[] grips;
    }

    public static class DirectionMath
    {
        public static int Select(float yaw, int previous, int count, float hysteresisDegrees)
        {
            float step = 360f / count;
            yaw = Mathf.Repeat(yaw, 360f);
            if (previous >= 0 && previous < count &&
                Mathf.Abs(Mathf.DeltaAngle(previous * step, yaw)) <= step * 0.5f + hysteresisDegrees)
                return previous;
            return Mathf.FloorToInt(yaw / step + 0.5f) % count;
        }

        public static float YawFromScreenPlane(Vector2 direction, float verticalGroundScale)
        {
            return Mathf.Atan2(direction.y / verticalGroundScale, direction.x) * Mathf.Rad2Deg;
        }
    }

    // Only sprites, PNG textures and JSON are used at runtime. No model or WebGL.
    [DisallowMultipleComponent]
    public sealed class Sibir128Character : MonoBehaviour
    {
        [SerializeField] private TextAsset definition;
        [SerializeField] private string initialLook = "axe";
        [SerializeField] private Texture2D[] atlasPages;
        [SerializeField] private SpriteRenderer visual;
        [SerializeField] private Transform groundRoot;
        [SerializeField] private Camera worldCamera;
        [SerializeField, Min(0.001f)] private float smoothTime = 0.095f;
        [SerializeField, Range(0f, 0.25f)] private float hysteresisDegrees = 0.12f;
        [SerializeField] private bool previewWalking;

        private static readonly Dictionary<TextAsset, SharedSprites> Libraries = new Dictionary<TextAsset, SharedSprites>();
        private sealed class SharedSprites
        {
            public TextAsset key; public AtlasDefinition data; public Sprite[] sprites; public Texture2D[] pages; public int refs;
        }
        private SharedSprites library;
        private SharedSprites pickupLibrary;
        private bool pickupPose;
        private readonly Dictionary<string, SharedSprites> equippedLibraries = new Dictionary<string, SharedSprites>();
        private Rigidbody2D body;
        public string EquipmentLook { get; private set; } = "axe";
        private int direction = 112, lastSprite = -1;
        private float visualYaw = 315f, targetYaw = 315f, yawVelocity;
        private double walkPhase;
        private Vector2 movementVelocity;
        private bool hasMovement;
        private Vector2? facingOverride;

        public SpriteRenderer Visual => visual;

        public void OverrideFacing(Vector2 direction)
        {
            facingOverride = direction.normalized;
        }

        public void ClearFacingOverride()
        {
            facingOverride = null;
        }

        public Vector2 AimDirection2D { get; private set; } = Vector2.right;
        public float TargetYawDegrees => Mathf.Repeat(targetYaw, 360f);
        public int DirectionIndex => direction;
        public double WalkPhase => walkPhase;
        public bool PreviewWalking { get => previewWalking; set => previewWalking = value; }

        public void Configure(TextAsset json, Texture2D[] pages, SpriteRenderer renderer, Camera camera)
        {
            definition = json; atlasPages = pages; visual = renderer; worldCamera = camera;
            groundRoot = transform;
        }

        public void SetMovementVelocity(Vector2 velocity)
        {
            // For actual forward locomotion: distance drives the shared phase.
            // Strafe/backwards animations are not included in this prototype.
            movementVelocity = velocity; hasMovement = true;
        }

        public static void ValidateDefinition(AtlasDefinition d)
        {
            if (d == null || d.schemaVersion != 1 || d.directionCount <= 0 ||
                d.pages == null || d.frames == null || d.animations == null ||
                d.pixelsPerUnit <= 0f || d.groundVerticalScale <= 0f)
                throw new ArgumentException("Invalid Sibir128 definition.");
            foreach (AtlasFrame f in d.frames)
            {
                if (f.page < 0 || f.page >= d.pages.Length || f.w <= 0 || f.h <= 0)
                    throw new ArgumentException("Invalid sprite rectangle.");
                AtlasPage p = d.pages[f.page];
                if (f.x < 0 || f.y < 0 || f.x + f.w > p.width || f.y + f.h > p.height ||
                    f.pivotX < 0 || f.pivotY < 0 || f.pivotX > f.w || f.pivotY > f.h ||
                    f.trimX + f.pivotX != d.rootX || f.trimY + f.pivotY != d.rootY)
                    throw new ArgumentException("Atlas bounds or ground pivot mismatch.");
            }
            foreach (AtlasClip clip in d.animations)
            {
                if (clip.phaseCount <= 0 || clip.frameIds == null || clip.frameIds.Length != clip.phaseCount * d.directionCount)
                    throw new ArgumentException("Invalid directional animation dimensions.");
                foreach (int id in clip.frameIds)
                    if (id < 0 || id >= d.frames.Length) throw new ArgumentException("Unknown sprite ID.");
            }
            if (d.animations.Length == 1 && d.animations[0].name == "pickup")
            {
                AtlasClip clip = d.animations[0];
                if (d.grips == null || d.grips.Length != clip.frameIds.Length || clip.fps <= 0 ||
                    d.grabPhase <= 0 || d.grabPhase >= clip.phaseCount - 1 || 128 % d.directionCount != 0)
                    throw new ArgumentException("Invalid pickup clip or grip samples.");
                return;
            }
            if (d.directionCount != 128 || d.animations.Length != 2 ||
                d.animations[0].name != "idle" || d.animations[1].name != "walk")
                throw new ArgumentException("Expected 128-direction idle and walk clips.");
        }

        private void Awake()
        {
            if (groundRoot == null) groundRoot = transform;
            body = groundRoot.GetComponentInParent<Rigidbody2D>();
            if (worldCamera == null) worldCamera = Camera.main;
            if (visual == null) visual = GetComponentInChildren<SpriteRenderer>();
            if (definition == null || visual == null || atlasPages == null)
            { Debug.LogError("Assign the Sibir128 JSON, atlas pages and SpriteRenderer.", this); enabled = false; return; }
            visual.flipX = false; visual.flipY = false;
            visual.drawMode = SpriteDrawMode.Simple;
            visual.spriteSortPoint = SpriteSortPoint.Pivot;

            try
            {
                library = Acquire(definition, atlasPages);
                EquipmentLook = initialLook;
                equippedLibraries.Add(initialLook, library);
                ApplyFrame(0, 0);
            }
            catch (Exception error)
            {
                Debug.LogException(error, this);
                enabled = false;
            }
        }

        private static SharedSprites Acquire(TextAsset asset, Texture2D[] pages)
        {
            if (Libraries.TryGetValue(asset, out SharedSprites shared))
            {
                if (pages.Length != shared.pages.Length)
                    throw new ArgumentException("Shared atlas reference mismatch.");
                for (int k = 0; k < pages.Length; k++)
                    if (pages[k] != shared.pages[k])
                        throw new ArgumentException("Use the same atlas pages for a shared definition.");
                shared.refs++;
                return shared;
            }

            AtlasDefinition data = JsonUtility.FromJson<AtlasDefinition>(asset.text);
            ValidateDefinition(data);
            if (pages.Length != data.pages.Length)
                throw new ArgumentException("Wrong atlas page count.");
            for (int k = 0; k < pages.Length; k++)
                if (pages[k] == null || pages[k].width != data.pages[k].width || pages[k].height != data.pages[k].height)
                    throw new ArgumentException("Atlas was resized on import. Check NPOT and max texture size.");

            shared = new SharedSprites { key = asset, data = data, sprites = new Sprite[data.frames.Length], pages = (Texture2D[])pages.Clone(), refs = 1 };
            Libraries.Add(asset, shared);
            return shared;
        }

        private static void Release(TextAsset asset, SharedSprites shared)
        {
            if (--shared.refs != 0) return;
            Libraries.Remove(asset);
            foreach (Sprite sprite in shared.sprites)
                if (sprite != null) Destroy(sprite);
        }

        public bool SetEquipmentLook(string look)
        {
            if (library == null || !isActiveAndEnabled || string.IsNullOrEmpty(look)) return false;
            if (EquipmentLook == look) return true;
            if (!equippedLibraries.TryGetValue(look, out SharedSprites next))
            {
                next = LoadLook(look);
                if (next == null) return false;
                equippedLibraries.Add(look, next);
            }

            library = next;
            EquipmentLook = look;
            lastSprite = -1;
            return true;
        }

        private SharedSprites LoadLook(string look)
        {
            string basePath = "Sibir128Looks/" + look;
            TextAsset asset = Resources.Load<TextAsset>(basePath + "/sibir128");
            if (asset == null) return null;

            try
            {
                AtlasDefinition data = JsonUtility.FromJson<AtlasDefinition>(asset.text);
                ValidateDefinition(data);
                if (data.rootX != library.data.rootX || data.rootY != library.data.rootY ||
                    data.pixelsPerUnit != library.data.pixelsPerUnit)
                    throw new ArgumentException("The equipped look must use the same ground pivot and scale.");
                var pages = new Texture2D[data.pages.Length];
                for (int k = 0; k < pages.Length; k++)
                {
                    string file = data.pages[k].file;
                    pages[k] = Resources.Load<Texture2D>(basePath + "/" + file.Substring(0, file.LastIndexOf('.')));
                }
                return Acquire(asset, pages);
            }
            catch (Exception error)
            {
                Debug.LogException(error, this);
                return null;
            }
        }

        public bool PreparePistolPickup()
        {
            if (library == null || !isActiveAndEnabled) return false;
            if (pickupLibrary == null)
                pickupLibrary = LoadLook("pistol-pickup");
            return pickupLibrary != null;
        }

        public int PickupDirections => pickupLibrary.data.directionCount;
        public int PickupGrab => pickupLibrary.data.grabPhase;
        public float PickupFps => pickupLibrary.data.animations[0].fps;
        public int PickupLastFrame => pickupLibrary.data.animations[0].phaseCount - 1;

        public Vector2 PickupFacing(int facing)
        {
            float yaw = facing * pickupLibrary.data.directionStepDegrees * Mathf.Deg2Rad;
            return new Vector2(Mathf.Cos(yaw), Mathf.Sin(yaw) * pickupLibrary.data.groundVerticalScale);
        }

        public Vector2 PickupGripOffset(int facing, int frame)
        {
            Vector2 grip = pickupLibrary.data.grips[frame * PickupDirections + facing];
            return visual.transform.TransformPoint(grip) - groundRoot.position;
        }

        public void ShowPickupFrame(int facing, int frame)
        {
            pickupPose = true;
            int id = pickupLibrary.data.animations[0].frameIds[frame * PickupDirections + facing];
            visual.sprite = GetSprite(pickupLibrary, id);
        }

        public void EndPickupPose(int facing)
        {
            if (!pickupPose) return;
            visualYaw = targetYaw = facing * pickupLibrary.data.directionStepDegrees;
            direction = DirectionMath.Select(visualYaw, -1, library.data.directionCount, 0f);
            yawVelocity = 0f;
            pickupPose = false;
            lastSprite = -1;
        }

        private void LateUpdate()
        {
            if (library == null || pickupPose || Time.deltaTime <= 0f) return;
            AtlasDefinition d = library.data;
            if (facingOverride.HasValue)
            {
                AimDirection2D = facingOverride.Value;
                targetYaw = DirectionMath.YawFromScreenPlane(AimDirection2D, d.groundVerticalScale);
            }
            else if (worldCamera != null && Mouse.current != null)
            {
                Vector2 mouse = Mouse.current.position.ReadValue();
                Ray ray = worldCamera.ScreenPointToRay(new Vector3(mouse.x, mouse.y, 0f));
                var plane = new Plane(Vector3.forward, groundRoot.position);
                if (plane.Raycast(ray, out float distance))
                {
                    Vector2 delta = ray.GetPoint(distance) - groundRoot.position;
                    if (delta.sqrMagnitude > 0.000625f)
                    {
                        AimDirection2D = delta.normalized; // Exact aim is independent of the selected sprite.
                        targetYaw = DirectionMath.YawFromScreenPlane(delta, d.groundVerticalScale);
                    }
                }
            }
            visualYaw = Mathf.SmoothDampAngle(visualYaw, targetYaw, ref yawVelocity, smoothTime,
                Mathf.Infinity, Time.deltaTime);
            direction = DirectionMath.Select(visualYaw, direction, d.directionCount, hysteresisDegrees);

            Vector2 velocity = hasMovement ? movementVelocity : body != null ? body.linearVelocity : Vector2.zero;
            bool drivenByMovement = hasMovement || body != null;
            bool walking = drivenByMovement ? velocity.sqrMagnitude > 0.0016f : previewWalking;
            if (walking)
            {
                double cycles;
                if (drivenByMovement)
                {
                    float groundSpeed = new Vector2(velocity.x, velocity.y / d.groundVerticalScale).magnitude;
                    float cycleDistance = d.cycleTravelB * d.pixelsPerB / d.pixelsPerUnit * Mathf.Abs(visual.transform.lossyScale.x);
                    cycles = groundSpeed * Time.deltaTime / Mathf.Max(cycleDistance, 0.0001f);
                    if (Vector2.Dot(velocity.normalized, AimDirection2D) < -.5f) cycles = -cycles;
                }
                else cycles = Time.deltaTime * d.animations[1].fps / d.animations[1].phaseCount;
                walkPhase += cycles;
                walkPhase -= Math.Floor(walkPhase);
            }
            // Heading or equipment changes preserve the phase of the step.
            int phase = walking ? (int)(walkPhase * d.animations[1].phaseCount) : 0;
            ApplyFrame(walking ? 1 : 0, phase);
        }

        private void ApplyFrame(int animation, int phase)
        {
            int id = library.data.animations[animation].frameIds[phase * library.data.directionCount + direction];
            if (id == lastSprite) return;
            visual.sprite = GetSprite(library, id);
            lastSprite = id;
        }

        private static Sprite GetSprite(SharedSprites shared, int id)
        {
            Sprite sprite = shared.sprites[id];
            if (sprite != null) return sprite;
            AtlasFrame frame = shared.data.frames[id];
            Texture2D texture = shared.pages[frame.page];
            var rect = new Rect(frame.x, texture.height - frame.y - frame.h, frame.w, frame.h);
            var pivot = new Vector2((float)frame.pivotX / frame.w, 1f - (float)frame.pivotY / frame.h);
            sprite = Sprite.Create(texture, rect, pivot, shared.data.pixelsPerUnit, 0,
                SpriteMeshType.FullRect, Vector4.zero, false);
            shared.sprites[id] = sprite;
            return sprite;
        }

        private void OnDestroy()
        {
            foreach (SharedSprites shared in equippedLibraries.Values)
                Release(shared.key, shared);
            equippedLibraries.Clear();
            if (pickupLibrary != null)
                Release(pickupLibrary.key, pickupLibrary);
            library = null;
        }
    }
}
