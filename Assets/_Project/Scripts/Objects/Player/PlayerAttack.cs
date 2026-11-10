namespace _Project.Scripts.Objects.Player
{
    using UnityEngine;
    using UnityEngine.InputSystem;
    using _Project.Scripts.Objects;

    public class PlayerAttack : MonoBehaviour
    {
        [SerializeField] private InputActionReference attackAction;
        [SerializeField] private Weapon weapon;

        private void OnEnable()
        {
            if (attackAction != null)
                attackAction.action.Enable();
        }

        private void OnDisable()
        {
            if (attackAction != null)
                attackAction.action.Disable();
        }

        private void Update()
        {
            if (attackAction != null && weapon != null &&
                attackAction.action.WasPressedThisFrame())
            {
                weapon.Attack();
            }
        }
    }
}