Shader "Shooter2D/Bunker Room Shade"
{
    Properties
    {
        _Opacity ("Opacity", Range(0, 1)) = 0
    }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "Queue"="Overlay" "RenderType"="Transparent" }
        Pass
        {
            Name "Room Shade"
            Tags { "LightMode"="SRPDefaultUnlit" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            ZTest Always
            Cull Off

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float _Opacity;
            CBUFFER_END

            float4 Vert(float3 position : POSITION) : SV_POSITION
            {
                return TransformObjectToHClip(position);
            }

            half4 Frag() : SV_Target
            {
                // The Level_01 camera clears to sRGB (8, 9, 10). Match it in linear space.
                const half3 bunkerBackground = half3(8, 9, 10) / (255 * 12.92);
                return half4(bunkerBackground, _Opacity);
            }
            ENDHLSL
        }
    }
}
