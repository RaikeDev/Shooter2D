using _Project.Scripts.Objects;
using UnityEngine;

namespace _Project.Scripts.Levels
{
    public sealed class BunkerDestructible : Damage
    {
        [SerializeField] private SpriteRenderer appearance;
        [SerializeField] private Sprite wreckage;
        [SerializeField] private Collider2D hitbox;

        protected override void Die()
        {
            appearance.sprite = wreckage;
            hitbox.enabled = false;
        }
    }
}
