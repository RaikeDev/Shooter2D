using UnityEngine;

namespace _Project.Scripts.Objects
{
    public class Door : MonoBehaviour
    {
        [SerializeField] private BoxCollider2D blockingCollider;
        [SerializeField] private SpriteRenderer doorSprite;
        [SerializeField] private Sprite openSprite;
        [SerializeField] private Sprite closedSprite;
        
        private void Awake()
        {
            if (closedSprite == null && doorSprite != null)
                closedSprite = doorSprite.sprite;
        }

        public void openDoor()
        {
            blockingCollider.enabled = false;
            doorSprite.enabled = openSprite != null;
            if (openSprite != null)
                doorSprite.sprite = openSprite;
        }

        public void closeDoor()
        {
            blockingCollider.enabled = true;
            doorSprite.enabled = true;
            doorSprite.sprite = closedSprite;
        }

        public void ToggleDoor()
        {
            if (blockingCollider.enabled)
            {
                openDoor();
            }
            else
            {
                closeDoor();
            }
        }
    }
}