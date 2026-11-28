using System.Collections.Generic;
using Sibir128;
using UnityEngine;

namespace _Project.Scripts.Objects.Player
{
    [RequireComponent(typeof(PlayerMovement), typeof(PlayerAttack), typeof(Rigidbody2D))]
    public sealed class PistolPickupSequence : MonoBehaviour
    {
        private const float StepLimit = .92f;
        private const float ArrivalTolerance = .009f;
        private const float ContactTolerance = .025f;
        private enum Phase { Idle, Approach, Pickup }
        private Phase phase;
        private WeaponPickup pickup;
        private Pistol pistol;
        private PlayerMovement motor;
        private PlayerAttack attack;
        private Sibir128Character character;
        private Collider2D body;
        private Rigidbody2D movementBody;
        private Vector2 stancePosition;
        private Vector2 approachOrigin;
        private float startedAt;
        private bool attached;
        private int heading;
        private ContactFilter2D solids;
        private readonly List<RaycastHit2D> hits = new();
        private SpriteRenderer liftedVisual;
        private Quaternion floorRotation;
        private Vector3 floorScale;
        private Vector2 socketLocal;

        public bool IsBusy => phase != Phase.Idle;
        public bool HasCharacterAnimation => character != null && character.PreparePistolPickup();

        private void Awake()
        {
            motor = GetComponent<PlayerMovement>();
            attack = GetComponent<PlayerAttack>();
            character = GetComponent<Sibir128Character>();
            movementBody = GetComponent<Rigidbody2D>();
            body = GetComponent<Collider2D>();
            solids = new ContactFilter2D { useTriggers = false };
            solids.SetLayerMask(Physics2D.GetLayerCollisionMask(gameObject.layer));
        }

        public bool TryBegin(WeaponPickup target)
        {
            if (IsBusy || body == null || target == null || target.Weapon is not Pistol chosen ||
                attack.CurrentWeapon == chosen || !HasCharacterAnimation || !target.TryReserve(this))
                return false;

            pickup = target;
            pistol = chosen;
            approachOrigin = movementBody.position;
            if (!TryFindStance(approachOrigin, pickup.GripWorld, out stancePosition, out heading))
            {
                Finish();
                return false;
            }

            phase = Phase.Approach;
            startedAt = Time.time;
            motor.MoveForPickup(stancePosition);
            attack.SetPickupFacing(character.PickupFacing(heading));
            return true;
        }

        private bool TryFindStance(Vector2 start, Vector2 grip, out Vector2 result, out int facing)
        {
            result = start;
            facing = 0;
            float best = StepLimit * StepLimit;
            bool found = false;
            for (int direction = 0; direction < character.PickupDirections; direction++)
            {
                // The catch frame sets the exact location of the feet. Move
                // the character to that point instead of bending a sprite arm.
                Vector2 candidate = grip - character.PickupGripOffset(direction, character.PickupGrab);
                float travel = (candidate - start).sqrMagnitude;
                if (travel >= best || (candidate - approachOrigin).sqrMagnitude > StepLimit * StepLimit ||
                    !ClearReach(candidate, grip) || !CanStep(start, candidate))
                    continue;

                best = travel;
                facing = direction;
                result = candidate;
                found = true;
            }
            return found;
        }

        private bool ClearReach(Vector2 from, Vector2 to)
        {
            Physics2D.Linecast(from, to, solids, hits);
            foreach (RaycastHit2D hit in hits)
                if (hit.collider != null && hit.rigidbody != movementBody &&
                    !hit.collider.transform.IsChildOf(transform))
                    return false;
            return true;
        }

        private bool CanStep(Vector2 from, Vector2 to)
        {
            Vector2 delta = to - from;
            float distance = delta.magnitude;
            if (distance <= ArrivalTolerance)
                return true;

            Vector2 direction = delta / distance;
            body.Cast(direction, solids, hits, distance + .01f);
            foreach (RaycastHit2D hit in hits)
                if (hit.collider != null && hit.rigidbody != movementBody &&
                    !hit.collider.transform.IsChildOf(transform) && Vector2.Dot(hit.normal, direction) < -.001f)
                    return false;
            return true;
        }

        private void Update()
        {
            if (phase == Phase.Idle)
                return;

            if (!attached && (pickup == null || pickup.Weapon != pistol))
            {
                Finish();
                return;
            }
            if (phase == Phase.Approach)
            {
                UpdateApproach();
                return;
            }

            float elapsed = Time.time - startedAt;
            int frame = Mathf.Min(character.PickupLastFrame, Mathf.FloorToInt(elapsed * character.PickupFps));
            if (!attached && frame >= character.PickupGrab)
            {
                character.ShowPickupFrame(heading, character.PickupGrab);
                if (!Grip())
                    Finish();
                else
                    startedAt = Time.time - character.PickupGrab / character.PickupFps;
                return;
            }

            character.ShowPickupFrame(heading, frame);
            if (attached && liftedVisual != null)
                UpdateLift(frame);
            if (elapsed >= (character.PickupLastFrame + 1) / character.PickupFps)
                Finish();
        }

        private void UpdateApproach()
        {
            Vector2 position = movementBody.position;
            if ((position - stancePosition).sqrMagnitude <= ArrivalTolerance * ArrivalTolerance)
            {
                Vector2 grip = pickup.GripWorld;
                if (!ClearReach(position, grip) ||
                    (position + character.PickupGripOffset(heading, character.PickupGrab) - grip).sqrMagnitude >
                        ContactTolerance * ContactTolerance)
                {
                    Finish();
                    return;
                }
                motor.MoveForPickup(stancePosition);
                phase = Phase.Pickup;
                startedAt = Time.time;
                character.ShowPickupFrame(heading, 0);
                return;
            }
            if (Time.time - startedAt > .9f || !CanStep(position, stancePosition))
            {
                if (Time.time - startedAt <= .9f &&
                    TryFindStance(position, pickup.GripWorld, out stancePosition, out heading))
                {
                    motor.MoveForPickup(stancePosition);
                    attack.SetPickupFacing(character.PickupFacing(heading));
                }
                else
                    Finish();
            }
        }

        private bool Grip()
        {
            SpriteRenderer floor = pickup.GetComponent<SpriteRenderer>();
            Vector2 hand = (Vector2)transform.position + character.PickupGripOffset(heading, character.PickupGrab);
            if ((hand - pickup.GripWorld).sqrMagnitude > ContactTolerance * ContactTolerance)
                return false;

            if (floor != null && floor.sprite != null)
            {
                liftedVisual = new GameObject("Pistol in Sibir's hand").AddComponent<SpriteRenderer>();
                liftedVisual.sprite = floor.sprite;
                liftedVisual.sharedMaterial = floor.sharedMaterial;
                liftedVisual.color = floor.color;
                liftedVisual.flipX = floor.flipX;
                liftedVisual.flipY = floor.flipY;
                liftedVisual.sortingLayerID = floor.sortingLayerID;
                liftedVisual.sortingOrder = floor.sortingOrder;
                liftedVisual.transform.SetPositionAndRotation(floor.transform.position, floor.transform.rotation);
                floorRotation = floor.transform.rotation;
                floorScale = floor.transform.lossyScale;
                liftedVisual.transform.localScale = floorScale;
                socketLocal = floor.transform.InverseTransformPoint(pickup.GripWorld);
            }

            FireWeapon oldWeapon = attack.CurrentWeapon as FireWeapon;
            attack.EquipWeapon(pistol);
            attached = true;
            pickup.Release(this);
            if (oldWeapon != null)
                pickup.SetWeapon(oldWeapon);
            else
            {
                pickup.gameObject.SetActive(false);
                Destroy(pickup.gameObject);
            }
            pickup = null;
            return true;
        }

        private void UpdateLift(int frame)
        {
            if (frame <= character.PickupGrab)
                return;

            float u = (frame - character.PickupGrab) / (float)(character.PickupLastFrame - character.PickupGrab);
            float blend = u * u * (3f - 2f * u);
            Vector2 aim = character.PickupFacing(heading);
            var heldRotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(aim.y, aim.x) * Mathf.Rad2Deg);
            Transform visual = liftedVisual.transform;
            visual.rotation = Quaternion.Slerp(floorRotation, heldRotation, blend);
            visual.localScale = Vector3.Lerp(floorScale, floorScale * .82f, blend);
            Vector2 hand = (Vector2)transform.position + character.PickupGripOffset(heading, frame);
            visual.position = (Vector3)hand - visual.TransformVector(socketLocal);
        }

        private void Finish()
        {
            if (pickup != null)
                pickup.Release(this);
            if (liftedVisual != null)
            {
                liftedVisual.enabled = false;
                Destroy(liftedVisual.gameObject);
            }
            if (motor != null)
                motor.EndPickupStep();
            if (character != null)
                character.EndPickupPose(heading);
            if (attack != null)
                attack.EndPickupFacing();
            pickup = null;
            pistol = null;
            liftedVisual = null;
            attached = false;
            phase = Phase.Idle;
        }

        private void OnDisable()
        {
            if (IsBusy)
                Finish();
        }
    }
}
