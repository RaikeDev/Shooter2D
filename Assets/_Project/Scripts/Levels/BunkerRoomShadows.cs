using System;
using System.Collections.Generic;
using UnityEngine;

namespace _Project.Scripts.Levels
{
    public sealed class BunkerRoomShadows : MonoBehaviour
    {
        [Serializable]
        public sealed class Room
        {
            public MeshRenderer shade;
            public Rect[] footprint;
            public Vector2[] sightTargets;

            [NonSerialized] internal float darkness;
        }

        [SerializeField] private Rigidbody2D player;
        [SerializeField] private Collider2D[] occluders;
        [SerializeField] private Room[] rooms;
        [SerializeField, Range(0.1f, 1f)] private float hiddenDarkness = .86f;
        [SerializeField, Min(0.1f)] private float glimpseDistance = 8f;
        [SerializeField, Min(0.1f)] private float fadeSeconds = .24f;

        private static readonly int Opacity = Shader.PropertyToID("_Opacity");
        private readonly List<RaycastHit2D> hits = new();
        private readonly HashSet<Collider2D> walls = new();
        private MaterialPropertyBlock properties;
        private ContactFilter2D sightFilter;

        public void Configure(Rigidbody2D actor, Collider2D[] wallsAndDoors, Room[] zones)
        {
            player = actor;
            occluders = wallsAndDoors;
            rooms = zones;
        }

        private void Start()
        {
            foreach (Collider2D occluder in occluders)
                if (occluder != null)
                    walls.Add(occluder);

            sightFilter = new ContactFilter2D { useTriggers = false };
            properties = new MaterialPropertyBlock();
            Refresh(immediate: true);
        }

        private void LateUpdate()
        {
            Refresh(immediate: false);
        }

        private void Refresh(bool immediate)
        {
            Vector2 position = player.position;
            foreach (Room room in rooms)
            {
                float target = CanSee(room, position) ? 0f : hiddenDarkness;
                room.darkness = immediate ? target : Mathf.MoveTowards(room.darkness, target, Time.deltaTime / fadeSeconds);
                room.shade.enabled = room.darkness > 0.001f;
                if (room.shade.enabled)
                {
                    properties.SetFloat(Opacity, room.darkness);
                    room.shade.SetPropertyBlock(properties);
                }
            }
        }

        private bool CanSee(Room room, Vector2 eye)
        {
            foreach (Rect area in room.footprint)
                if (area.Contains(eye))
                    return true;

            foreach (Vector2 sample in room.sightTargets)
            {
                if ((sample - eye).sqrMagnitude > glimpseDistance * glimpseDistance)
                    continue;

                Physics2D.Linecast(eye, sample, sightFilter, hits);
                bool blocked = false;
                foreach (RaycastHit2D hit in hits)
                {
                    if (!walls.Contains(hit.collider))
                        continue;
                    blocked = true;
                    break;
                }
                if (!blocked)
                    return true;
            }
            return false;
        }
    }
}
