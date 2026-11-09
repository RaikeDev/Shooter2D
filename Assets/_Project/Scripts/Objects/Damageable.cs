namespace _Project.Scripts.Objects
{
    using UnityEngine;
    public class Damageable : MonoBehaviour
    {
        [SerializeField, Min(1)]
        private int maxHealth = 100;

        public int Health { get; private set; }
        public bool IsDead { get; private set; }

        protected virtual void Awake()
        {
            Health = maxHealth;
        }

        public void TakeDamage(int damage)
        {
            if (IsDead || damage <= 0)
                return;

            Health = Mathf.Max(0, Health - damage); // проверка на урон больший здоровья
            IsDead = Health == 0; // присваивает IsDead true/false в зависимости от Health

            OnHit();

            if (IsDead)
                Die();
        }

        protected virtual void OnHit()
        {
            
        }

        protected virtual void Die()
        {
            Destroy(gameObject);
        }
    }
}