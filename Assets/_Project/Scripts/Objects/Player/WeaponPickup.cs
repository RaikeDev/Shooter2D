using UnityEngine;

namespace _Project.Scripts.Objects.Player
{
    public class WeaponPickup : MonoBehaviour
    {
        [SerializeField] private FireWeapon weapon;
        [SerializeField] private Vector2 pistolGripLocal = new(.035f, -.105f);
        private PistolPickupSequence reservedBy;

        public FireWeapon Weapon => weapon;
        public bool IsReserved => reservedBy != null;
        public Vector2 GripWorld => transform.TransformPoint(pistolGripLocal);

        public bool TryReserve(PistolPickupSequence owner)
        {
            if (IsReserved)
                return false;
            reservedBy = owner;
            return true;
        }

        public void Release(PistolPickupSequence owner)
        {
            if (reservedBy == owner)
                reservedBy = null;
        }

        public void SetWeapon(FireWeapon newWeapon)
        {
            weapon = newWeapon;
            GetComponent<SpriteRenderer>().sprite = weapon.PickupSprite;
        }
    }
}
