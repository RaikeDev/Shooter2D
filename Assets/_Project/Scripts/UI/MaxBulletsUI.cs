using TMPro;
using UnityEngine;
using _Project.Scripts.Objects;
using _Project.Scripts.Objects.Player;

namespace _Project.Scripts.UI
{
    public class MaxBullets : MonoBehaviour
    {
        [SerializeField] private TMP_Text maxBulletsText;
        [SerializeField] private PlayerAttack playerAttack;
        
        private void LateUpdate()
        {
            if (playerAttack.CurrentWeapon is FireWeapon gun)
            {
                maxBulletsText.enabled = true;
                maxBulletsText.text = $"Max {gun.MaxBullet}";
            }
            else
            {
                maxBulletsText.enabled = false;
            }
        }
    }
}