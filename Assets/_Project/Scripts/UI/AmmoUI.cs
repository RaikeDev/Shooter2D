using TMPro;
using UnityEngine;
using _Project.Scripts.Objects;
using _Project.Scripts.Objects.Player;

namespace _Project.Scripts.UI
{
    public class AmmoUI : MonoBehaviour
    {
        [SerializeField] private PlayerAttack playerAttack;
        [SerializeField] private TMP_Text ammoText;

        private void LateUpdate()
        {
            if (playerAttack.CurrentWeapon is FireWeapon gun)
            {
                ammoText.enabled = true;
                ammoText.text = $"{gun.BulletsCount} / {gun.ReserveAmmo}";
            }
            else
            {
                ammoText.enabled = false;
            }
        }
    }
}