using UnityEngine;

namespace _Project.Scripts.Objects
{
    public class Door : MonoBehaviour
    {
        [SerializeField] private BoxCollider2D blockingCollider;
        [SerializeField] private SpriteRenderer doorSprite;
        [SerializeField] private Sprite openSprite;
        [SerializeField] private Sprite closedSprite;
        
        public void openDoor()
        {
            blockingCollider.enabled = false;
            doorSprite.enabled = false;
            //doorSprite.sprite = openSprite; раскоментить когда будут спрайты
        }

        public void closeDoor()
        {
            blockingCollider.enabled = true;
            doorSprite.enabled = true;
            //doorSprite.sprite = closedSprite; раскоментить когда будут спрайты
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