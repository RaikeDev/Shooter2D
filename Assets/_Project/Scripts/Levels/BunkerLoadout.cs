using _Project.Scripts.Objects;
using _Project.Scripts.Objects.Player;
using UnityEngine;
using UnityEngine.InputSystem;

namespace _Project.Scripts.Levels
{
    [RequireComponent(typeof(PlayerAttack), typeof(Axe))]
    public sealed class BunkerLoadout : MonoBehaviour
    {
        [SerializeField] private InputAction switchWeapon = new("Switch axe and firearm", InputActionType.Button, "<Keyboard>/q");

        private PlayerAttack player;
        private Axe axe;
        private FireWeapon holstered;

        private void Awake()
        {
            player = GetComponent<PlayerAttack>();
            axe = GetComponent<Axe>();
        }

        private void OnEnable() => switchWeapon.Enable();
        private void OnDisable() => switchWeapon.Disable();
        private void OnDestroy() => switchWeapon.Dispose();

        private void Update()
        {
            if (!switchWeapon.WasPressedThisFrame())
                return;

            if (player.CurrentWeapon is FireWeapon current)
            {
                holstered = current;
                player.EquipWeapon(axe);
            }
            else if (player.CurrentWeapon == axe && holstered != null)
            {
                player.EquipWeapon(holstered);
            }
        }
    }
}
