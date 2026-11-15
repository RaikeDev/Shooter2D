using UnityEngine;
using System.Collections;
using System.Collections.Generic;
namespace _Project.Scripts.Objects
{
    public class Axe : Weapon
    {
        [SerializeField] private Transform axeSwingPivot;
        private bool isSwinging;

        private IEnumerator Swing(Vector2 direction)
        {
            isSwinging = true;
            float aimAngle = Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg;
            const float duration = 0.3f;

            for (float elapsed = 0f; elapsed < duration; elapsed += Time.deltaTime)
            {
                float angle = Mathf.Lerp(-45f, 45f, elapsed / duration);
                axeSwingPivot.rotation = Quaternion.Euler(0f, 0f, aimAngle + angle);
                yield return null;
            }

            axeSwingPivot.localRotation = Quaternion.identity;
            isSwinging = false;
        }
        
        public override void Attack(Vector2 direction)
        {
            if (isSwinging)
                return;
            StartCoroutine(Swing(direction));
            
            Vector2 origin = transform.position;
            var damagedTargets = new HashSet<Damage>();

            foreach (Collider2D collider in Physics2D.OverlapCircleAll(origin, 1.5f))
            {
                if (collider.transform.IsChildOf(transform))
                    continue;

                Vector2 toTarget = (Vector2)collider.bounds.center - origin;
                if (Vector2.Angle(direction, toTarget) > 45f)
                    continue;

                Damage target = collider.GetComponentInParent<Damage>();
                if (target != null && damagedTargets.Add(target))
                    target.TakeDamage(DamageAmount);
            }
        }
    }
}