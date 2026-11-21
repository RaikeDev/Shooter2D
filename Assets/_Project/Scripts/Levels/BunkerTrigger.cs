using UnityEngine;

namespace _Project.Scripts.Levels
{
    [RequireComponent(typeof(BoxCollider2D))]
    public sealed class BunkerTrigger : MonoBehaviour
    {
        public enum Kind { Checkpoint, Hazard, Exit }

        [SerializeField] private BunkerLevel level;
        [SerializeField] private Kind kind;
        [SerializeField] private Vector2 checkpointPosition;

        public void Configure(BunkerLevel owner, Kind role, Vector2 respawn)
        {
            level = owner;
            kind = role;
            checkpointPosition = respawn;
        }

        private void OnTriggerEnter2D(Collider2D contact)
        {
            if (!level.IsPlayer(contact))
                return;

            switch (kind)
            {
                case Kind.Checkpoint:
                    level.RecordCheckpoint(checkpointPosition);
                    break;
                case Kind.Hazard:
                    level.ResetAtCheckpoint();
                    break;
                case Kind.Exit:
                    level.ReachExit();
                    break;
            }
        }
    }
}
