using System;
using UnityEngine;
using UnityEngine.InputSystem;
namespace _Project.Scripts.Objects.Player
{
    public class PlayerInteraction : MonoBehaviour
    {
        private Door nearDoor;
        [SerializeField] private InputActionReference interaction;

        private void OnTriggerEnter2D(Collider2D other)
        {
            Door door = other.GetComponentInParent<Door>();
            if (door != null)
                nearDoor = door;
        }

        private void OnTriggerExit2D(Collider2D other)
        {
            Door door = other.GetComponentInParent<Door>();
            if (door == nearDoor)
                nearDoor = null;
        }

        public void OnEnable()
        {
            if (interaction != null)
            {
                interaction.action.Enable();
            }
        }
        public void OnDisable(){
            if (interaction != null)
            {
                interaction.action.Disable();
            }
        }

        private void Update()
        {
            if (interaction == null || !interaction.action.WasPressedThisFrame())
                return;

            Vector2 playerPosition = transform.position;
            WeaponPickup nearestPickup = null;
            float nearestDistance = float.PositiveInfinity;

            foreach (Collider2D collider in Physics2D.OverlapCircleAll(playerPosition, 0.5f))
            {
                WeaponPickup pickup = collider.GetComponentInParent<WeaponPickup>();
                if (pickup == null || pickup.Weapon == null)
                    continue;

                float distance = Vector2.Distance(playerPosition, pickup.transform.position);
                if (distance < nearestDistance)
                {
                    nearestPickup = pickup;
                    nearestDistance = distance;
                }
            }
            
            if (nearDoor != null) nearDoor.ToggleDoor();
            if (nearestPickup == null) return;
            
            PlayerAttack playerAttack = GetComponent<PlayerAttack>();
            FireWeapon newWeapon = nearestPickup.Weapon;
            FireWeapon oldWeapon = playerAttack.CurrentWeapon as FireWeapon;

            if (oldWeapon == newWeapon)
                return;

            playerAttack.EquipWeapon(newWeapon);

            if (oldWeapon != null)
                nearestPickup.SetWeapon(oldWeapon);
            else
                Destroy(nearestPickup.gameObject);
        }
    }
}