namespace _Project.Scripts.Objects
{
    public class ShotGun : FireWeapon
    {
        protected override void Shoot()
        {
            SpawnBullet(-10f, 0.3f);
            SpawnBullet(0f, 0.3f);
            SpawnBullet(10f, 0.3f);
            SpawnBullet(-5f, 0.3f);
            SpawnBullet(5f, 0.3f);
        }
    }
}