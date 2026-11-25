using System;
using UnityEngine;
namespace _Project.Scripts.Objects
{
    public class FireWeapon : Weapon
    {
        [SerializeField, Min(1)] private int maxBullet;
        private int bulletsCount;
        [SerializeField, Min(0)] private int reserveAmmo;
        [SerializeField] private Bullet bulletPrefab;
        [SerializeField] private Transform firePoint;
        [SerializeField] private Vector2 muzzleOffset;
        [SerializeField] private SpriteRenderer weaponSpriteRenderer;
        [SerializeField] private Sprite pickupSprite;
        public Sprite PickupSprite => pickupSprite;
        public int BulletsCount => bulletsCount;
        public int MaxBullet => maxBullet;
        public int ReserveAmmo => reserveAmmo;
        
        public void SetEquipped(bool equipped)
        {
            if (weaponSpriteRenderer == null)
                return;

            if (equipped)
                weaponSpriteRenderer.sprite = pickupSprite;

            weaponSpriteRenderer.enabled = equipped;
        }
        
        public void Start()
        {
            bulletsCount = maxBullet;
        }

        public void fire()
        {
            if (IsInvoking(nameof(FinishReload))) return;
            if (bulletsCount > 0)
            {
                Shoot();
                bulletsCount--;
            }
            else
            {
                reload();
            }
        }

        public void reload()
        {
            if (reserveAmmo <= 0 || bulletsCount >= maxBullet) return;
            if (IsInvoking(nameof(FinishReload))) return;
            Invoke(nameof(FinishReload), 2f);
        }

        private void FinishReload()
        {
            int missingAmmo = maxBullet - bulletsCount;
            int loadedAmmo = Math.Min(reserveAmmo, missingAmmo);
            bulletsCount += loadedAmmo;
            reserveAmmo -=  loadedAmmo;
        }
        
        public override void Attack(Vector2 direction)
        {
            fire();
        }
        protected virtual void Shoot()
        {
            SpawnBullet(0f);
        }

        protected void SpawnBullet(float angle, float lifetime = 2f)
        {
            Quaternion rotation = firePoint.rotation * Quaternion.Euler(0f, 0f, angle);
            Vector3 spawnPosition = firePoint.TransformPoint(muzzleOffset);
            Bullet bullet = Instantiate(bulletPrefab, spawnPosition, rotation);
            Collider2D shooterCollider = GetComponentInParent<Collider2D>();
            Collider2D bulletCollider = bullet.GetComponent<Collider2D>();
            if (shooterCollider != null && bulletCollider != null) Physics2D.IgnoreCollision(bulletCollider, shooterCollider);
            Destroy(bullet.gameObject, lifetime);
            bullet.SetDamage(DamageAmount);

            Rigidbody2D rb = bullet.GetComponent<Rigidbody2D>();
            rb.AddForce(bullet.transform.right * bulletPrefab.getSpeed(), ForceMode2D.Impulse);
        }
    }
}