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
            if (interaction != null && nearDoor != null && interaction.action.WasPressedThisFrame())
            {
                nearDoor.ToggleDoor();
            }
        }
    }
}