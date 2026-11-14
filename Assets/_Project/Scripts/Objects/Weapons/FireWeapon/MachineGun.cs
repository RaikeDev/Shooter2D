using System;
using UnityEngine;
namespace _Project.Scripts.Objects
{
    public class MachineGun : FireWeapon
    {
        private float nextShotTime;

        public override void Attack(Vector2 direction)
        {
            if (Time.time < nextShotTime)
                return;

            nextShotTime = Time.time + 0.1f;
            base.Attack(direction);
        }
    }
}