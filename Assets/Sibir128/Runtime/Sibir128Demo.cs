using UnityEngine;
using UnityEngine.InputSystem;

namespace Sibir128
{
    // Optional preview input only: Space toggles the walk cycle in place.
    public sealed class Sibir128Demo : MonoBehaviour
    {
        private Sibir128Character character;
        private void Awake() => character = GetComponent<Sibir128Character>();
        private void Update()
        {
            if (character != null && Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame)
                character.PreviewWalking = !character.PreviewWalking;
        }
    }
}
