using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

public class PlayerMovement : MonoBehaviour
{
    private Rigidbody2D rb;

    [SerializeField]
    private InputActionReference moveAction;
    private Vector2 moveInput;
    [SerializeField]
    private float speed;
    void Start()
    {
        speed = 5f;
    }


    void Update()
    {
        moveInput = moveAction.action.ReadValue<Vector2>();
    }

    void FixedUpdate()
    {
        rb.linearVelocity = moveInput * speed;
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
