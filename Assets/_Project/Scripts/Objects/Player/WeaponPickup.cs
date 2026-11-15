using UnityEngine;

namespace _Project.Scripts.Objects.Player
{
    public class WeaponPickup : MonoBehaviour
    {
        [SerializeField] private FireWeapon weapon;

        public FireWeapon Weapon => weapon;

        public void SetWeapon(FireWeapon newWeapon)
        {
            weapon = newWeapon;
            GetComponent<SpriteRenderer>().sprite = weapon.PickupSprite;
        }
    }
}