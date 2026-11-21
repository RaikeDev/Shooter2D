using UnityEngine;

namespace _Project.Scripts.Levels
{
    public sealed class BunkerLevel : MonoBehaviour
    {
        [SerializeField] private Rigidbody2D player;
        [SerializeField] private Camera viewCamera;
        [SerializeField, Range(0f, 55f)] private float viewPitch;
        [SerializeField] private Transform[] sharedWallFaces = System.Array.Empty<Transform>();
        [SerializeField] private SpriteRenderer stairDoorFace;
        [SerializeField] private Transform stairDoorSill;
        [SerializeField] private Vector2 startPoint;
        [SerializeField] private Rect cameraBounds;
        [SerializeField] private GameObject exitReadyLight;
        [SerializeField] private GameObject exitCompleteLight;

        private Vector2 respawnPoint;
        private Vector3 cameraVelocity;
        private bool checkpointReached;
        private bool finished;
        private bool pendingRespawn;
        private float ignoreHazardsUntil;

        public void Configure(Rigidbody2D actor, Camera camera, Vector2 spawn, Rect bounds,
            GameObject readyLight, GameObject completeLight)
        {
            player = actor;
            viewCamera = camera;
            startPoint = spawn;
            cameraBounds = bounds;
            exitReadyLight = readyLight;
            exitCompleteLight = completeLight;
            InitializeView();
        }

        private void Awake()
        {
            respawnPoint = startPoint;
            InitializeView();
        }

        private void LateUpdate()
        {
            if (player == null)
                return;

            Vector3 target = CameraPosition(player.position);
            UpdateWallFaces();
            UpdateStairDoorLayer();
            viewCamera.transform.position = Vector3.SmoothDamp(viewCamera.transform.position, target,
                ref cameraVelocity, 0.16f);
        }

        private void InitializeView()
        {
            viewCamera.transform.rotation = Quaternion.Euler(-viewPitch, 0f, 0f);
            viewCamera.transform.position = CameraPosition(startPoint);
            UpdateWallFaces();
            UpdateStairDoorLayer();
        }

        private void UpdateWallFaces()
        {
            foreach (Transform face in sharedWallFaces)
            {
                if (face == null)
                    continue;

                bool visible = player.position.y < face.position.y;
                if (face.gameObject.activeSelf != visible)
                    face.gameObject.SetActive(visible);
            }
        }

        private void UpdateStairDoorLayer()
        {
            if (stairDoorFace == null || stairDoorSill == null)
                return;

            float distance = player.position.y - stairDoorSill.position.y;
            bool behind = distance > 0f;
            stairDoorFace.sortingOrder = behind ? 35 : 23;

            // The stairwell lies behind the raised door when viewed from the main hall.
            Color tint = stairDoorFace.color;
            tint.a = behind ? Mathf.Lerp(.70f, 1f, Mathf.InverseLerp(.75f, 1.70f, distance)) : 1f;
            stairDoorFace.color = tint;
        }

        private Vector3 CameraPosition(Vector2 focus)
        {
            float halfHeight = viewCamera.orthographicSize;
            float halfWidth = halfHeight * viewCamera.aspect;
            float floorHalfHeight = halfHeight / Mathf.Cos(viewPitch * Mathf.Deg2Rad);
            var center = new Vector3(
                FrameAxis(focus.x, cameraBounds.xMin, cameraBounds.xMax, halfWidth),
                FrameAxis(focus.y, cameraBounds.yMin, cameraBounds.yMax, floorHalfHeight),
                0f);
            return center - viewCamera.transform.forward * 18f;
        }

        private static float FrameAxis(float position, float min, float max, float halfSize)
        {
            return max - min > 2f * halfSize
                ? Mathf.Clamp(position, min + halfSize, max - halfSize)
                : (min + max) * 0.5f;
        }

        internal bool IsPlayer(Collider2D contact)
        {
            return contact.attachedRigidbody == player && !contact.isTrigger;
        }

        internal void RecordCheckpoint(Vector2 position)
        {
            if (checkpointReached || finished)
                return;

            checkpointReached = true;
            respawnPoint = position;
        }

        internal void ResetAtCheckpoint()
        {
            if (finished || Time.time < ignoreHazardsUntil)
                return;

            ignoreHazardsUntil = Time.time + 0.5f;
            pendingRespawn = true;
        }

        private void FixedUpdate()
        {
            if (!pendingRespawn)
                return;

            pendingRespawn = false;
            player.linearVelocity = Vector2.zero;
            player.angularVelocity = 0;
            player.position = respawnPoint;
            cameraVelocity = Vector3.zero;
            viewCamera.transform.position = CameraPosition(respawnPoint);
        }

        internal void ReachExit()
        {
            if (finished)
                return;

            finished = true;
            exitReadyLight.SetActive(false);
            exitCompleteLight.SetActive(true);
        }
    }
}
