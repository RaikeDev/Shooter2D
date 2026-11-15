using System;
using System.Drawing;
using UnityEngine;

namespace _Project.Scripts.Objects
{
    public class Bullet : MonoBehaviour
    {
        private Rigidbody2D rb;
        [SerializeField] private int speed;
        [SerializeField] private BoxCollider2D boxCollider2D;
        private int damage;

        public void SetDamage(int amount)
        {
            damage = amount;
        }
        public void Awake()
        {
            speed = 100;
        }

        public int getSpeed()
        {
            return speed;
        }
        public void trace(Vector2 direction)
        {
            
        }
        private void OnCollisionEnter2D(Collision2D collision)
        {
            Damage target = collision.collider.GetComponentInParent<Damage>();

            if (target != null)
                target.TakeDamage(damage);

            Destroy(gameObject);
        }
    }
}