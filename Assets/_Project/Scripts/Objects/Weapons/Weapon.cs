using UnityEngine;

namespace _Project.Scripts.Objects
{
    public class Weapon : MonoBehaviour
    {
        [SerializeField, Min(1)]
        private int damage;

        private void OnTriggerEnter2D(Collider2D other)
        {
            var target = other.GetComponentInParent<Damageable>();

            if (target != null)
                target.TakeDamage(damage);
        }
        
        public virtual void Attack()
        {
            //анимация атаки
        }
    }
}