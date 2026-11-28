namespace _Project.Scripts.Objects.Player
{
    using UnityEngine;
    using Sibir128;
    using UnityEngine.InputSystem;
    using _Project.Scripts.Objects;

    public class PlayerAttack : MonoBehaviour
    {
        [SerializeField] private InputActionReference attackAction;
        [SerializeField] private Weapon weapon;
        [SerializeField] private GameObject axeVisual;
        [SerializeField] private Camera aimCamera;
        [SerializeField] private Transform aimPivot;

        private bool pickupFacing;
        private Sibir128Character character;

        public void SetPickupFacing(Vector2 direction)
        {
            pickupFacing = true;
            character?.OverrideFacing(direction);
            if (aimPivot != null)
                aimPivot.rotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg);
        }

        public void EndPickupFacing()
        {
            pickupFacing = false;
            character?.ClearFacingOverride();
            ShowEquippedVisual();
        }

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
            bool showAxe = weapon is Axe;
            if (axeVisual != null && axeVisual.activeSelf != showAxe)
                axeVisual.SetActive(showAxe);
            
            if (pickupFacing) return;

            if (Mouse.current == null || aimCamera == null || aimPivot == null) return;
            
            Vector2 mousePosition = Mouse.current.position.ReadValue();
            Ray ray = aimCamera.ScreenPointToRay(mousePosition);
            Plane aimPlane = new Plane(Vector3.forward, aimPivot.position);

            if (!aimPlane.Raycast(ray, out float distance)) return;

            Vector2 direction = ray.GetPoint(distance) - aimPivot.position;
           
            if (direction.sqrMagnitude < 0.0001f) return;
            
            direction.Normalize();
            
            float angle = Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg;
            
            aimPivot.rotation = Quaternion.Euler(0f, 0f, angle);
            
            if (attackAction ==null || weapon == null) return;
            if (attackAction.action.WasPressedThisFrame() || (weapon is MachineGun && attackAction.action.IsPressed())) weapon.Attack(direction);
        }
        
        private void Awake()
        {
            character = GetComponent<Sibir128Character>();
        }

        private void Start()
        {
            EquipWeapon(weapon);
        }

        public void EquipWeapon(Weapon newWeapon)
        {
            if (weapon is FireWeapon oldGun)
                oldGun.SetEquipped(false);

            weapon = newWeapon;

            if (!pickupFacing)
                ShowEquippedVisual();
        }

        private void ShowEquippedVisual()
        {
            string look = weapon is Pistol ? "pistol" : "unarmed";
            bool baked = character != null && character.SetEquipmentLook(look) && look == "pistol";
            if (weapon is FireWeapon equippedGun)
                equippedGun.SetEquipped(!baked);
        }
        
        public Weapon CurrentWeapon => weapon;
    }
}