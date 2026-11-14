using UnityEngine;
namespace _Project.Scripts.Objects
{
    public class FireWeapon : Weapon
    {
        [SerializeField, Min(1)] private int maxBullet;
        private int bulletsCount;
        [SerializeField] private Bullet bulletPrefab;
        [SerializeField] private Transform firePoint;

        public void Start()
        {
            bulletsCount = maxBullet;
        }

        public void fire()
        {
            if (bulletsCount > 0)
            {
                Bullet bullet = Instantiate(bulletPrefab, firePoint.position, firePoint.rotation);
                bullet.SetDamage(DamageAmount);
                Rigidbody2D rb = bullet.GetComponent<Rigidbody2D>();
                rb.AddForce(firePoint.right * bulletPrefab.getSpeed(), ForceMode2D.Impulse);
                bulletsCount--;
            }
            else
            {
                reload();
            }
        }

        public void reload()
        {
            if (IsInvoking(nameof(FinishReload))) return;
            Invoke(nameof(FinishReload), 2f);
        }

        private void FinishReload()
        {
            bulletsCount = maxBullet;
        }
        
        public override void Attack(Vector2 direction)
        {
            fire();
        }
    }
}