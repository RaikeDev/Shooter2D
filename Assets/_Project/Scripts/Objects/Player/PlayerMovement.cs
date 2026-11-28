using UnityEngine;
using UnityEngine.InputSystem;

public class PlayerMovement : MonoBehaviour
{
    private Rigidbody2D rb;

    [SerializeField]
    private InputActionReference moveAction;
    private Vector2 moveInput;
    private Vector2 pickupTarget;
    private bool pickupStep;

    public void MoveForPickup(Vector2 target)
    {
        pickupTarget = target;
        pickupStep = true;
    }

    public void EndPickupStep()
    {
        pickupStep = false;
    }
    [SerializeField]
    private float speed = 5f;
    void Start()
    {
        if (speed <= 0f)
            speed = 5f;
    }


    void Update()
    {
        moveInput = moveAction.action.ReadValue<Vector2>();
    }

    void FixedUpdate()
    {
        rb.linearVelocity = pickupStep
            ? Vector2.ClampMagnitude((pickupTarget - rb.position) / Time.fixedDeltaTime, Mathf.Min(speed, 2.7f))
            : moveInput * speed;
    }

    void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    void OnEnable()
    {
        moveAction.action.Enable();
    }

    void OnDisable()
    {
        moveAction.action.Disable();
    }
}
