using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Sibir128.Editor
{
    public sealed class Sibir128TextureImport : AssetPostprocessor
    {
        private void OnPreprocessTexture()
        {
            if ((!assetPath.Contains("/Sibir128/") && !assetPath.Contains("/Sibir128Looks/")) || !Path.GetFileName(assetPath).StartsWith("sibir128-atlas-", StringComparison.Ordinal)) return;
            var importer = (TextureImporter)assetImporter;
            importer.textureType = TextureImporterType.Default;
            importer.filterMode = FilterMode.Point; importer.wrapMode = TextureWrapMode.Clamp;
            importer.mipmapEnabled = false; importer.isReadable = false;
            importer.sRGBTexture = true; importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false; importer.npotScale = TextureImporterNPOTScale.None;
            importer.textureCompression = TextureImporterCompression.Uncompressed; importer.maxTextureSize = 2048;
        }
    }

    public static class Sibir128Tools
    {
        private static TextAsset FindDefinition()
        {
            foreach (string guid in AssetDatabase.FindAssets("sibir128 t:TextAsset"))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.EndsWith("/Sibir128/sibir128.json", StringComparison.Ordinal)) return AssetDatabase.LoadAssetAtPath<TextAsset>(path);
            }
            throw new InvalidOperationException("Copy Assets/Sibir128 into the Unity project's Assets folder first.");
        }

        private static Texture2D[] Pages(TextAsset definition, AtlasDefinition data)
        {
            string folder = Path.GetDirectoryName(AssetDatabase.GetAssetPath(definition)).Replace('\\', '/');
            var pages = new Texture2D[data.pages.Length];
            for (int k = 0; k < pages.Length; k++) pages[k] = AssetDatabase.LoadAssetAtPath<Texture2D>(folder + "/" + data.pages[k].file);
            return pages;
        }

        [MenuItem("Tools/Sibir128/Reimport Atlases")]
        public static void ReimportAtlases()
        {
            TextAsset definition = FindDefinition(); AtlasDefinition data = JsonUtility.FromJson<AtlasDefinition>(definition.text);
            string folder = Path.GetDirectoryName(AssetDatabase.GetAssetPath(definition)).Replace('\\', '/');
            foreach (AtlasPage page in data.pages)
                AssetDatabase.ImportAsset(folder + "/" + page.file, ImportAssetOptions.ForceUpdate);
        }

        [MenuItem("Tools/Sibir128/Validate Package")]
        public static void ValidatePackage()
        {
            TextAsset definition = FindDefinition(); AtlasDefinition data = JsonUtility.FromJson<AtlasDefinition>(definition.text);
            Sibir128Character.ValidateDefinition(data); Texture2D[] pages = Pages(definition, data);
            for (int k = 0; k < pages.Length; k++)
            {
                if (pages[k] == null || pages[k].width != data.pages[k].width || pages[k].height != data.pages[k].height)
                    throw new InvalidOperationException("Atlas size changed on import.");
                var importer = (TextureImporter)AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(pages[k]));
                if (importer.filterMode != FilterMode.Point || importer.mipmapEnabled || importer.isReadable || importer.npotScale != TextureImporterNPOTScale.None)
                    throw new InvalidOperationException("Incorrect texture import settings.");
            }
            var seen = new bool[128]; float step = 360f / 128;
            for (int k = 0; k < 36000; k++)
            {
                float yaw = k / 100f; int index = DirectionMath.Select(yaw, -1, 128, 0f); seen[index] = true;
                if (Mathf.Abs(Mathf.DeltaAngle(yaw, index * step)) > step * .5f + .0001f)
                    throw new InvalidOperationException("Direction selection error.");
            }
            foreach (bool visited in seen) if (!visited) throw new InvalidOperationException("Missing direction.");
            if (DirectionMath.Select(359.9f, 0, 128, .12f) != 0 || DirectionMath.Select(.1f, 0, 128, .12f) != 0)
                throw new InvalidOperationException("Wrap boundary instability.");
            Debug.Log("Sibir128: atlas bounds, pivots, import settings, all 128 directions and wrap validated.");
        }

        [MenuItem("Tools/Sibir128/Create 2D Preview Scene")]
        public static void CreatePreviewScene()
        {
            ReimportAtlases(); ValidatePackage(); TextAsset definition = FindDefinition();
            AtlasDefinition data = JsonUtility.FromJson<AtlasDefinition>(definition.text); Texture2D[] pages = Pages(definition, data);
            Shader shader = Shader.Find("Universal Render Pipeline/2D/Sprite-Unlit-Default");
            if (shader == null) shader = Shader.Find("Sprites/Default");
            if (shader == null) throw new InvalidOperationException("No compatible unlit sprite shader is available.");
            string materialPath = Path.GetDirectoryName(AssetDatabase.GetAssetPath(definition)).Replace('\\', '/') + "/Sibir128-Unlit.mat";
            Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, materialPath); }
            else if (material.shader != shader) { material.shader = shader; EditorUtility.SetDirty(material); }
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive); SceneManager.SetActiveScene(scene);
            var cameraObject = new GameObject("Sibir128 2D Camera"); var camera = cameraObject.AddComponent<Camera>();
            cameraObject.tag = "MainCamera"; camera.orthographic = true; camera.orthographicSize = 2.1f;
            camera.transform.position = new Vector3(0f, .65f, -10f); camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(.24f, .28f, .29f);
            var ground = new GameObject("Sibir128 Ground Root"); var visual = new GameObject("Sprite Visual"); visual.transform.SetParent(ground.transform, false);
            var renderer = visual.AddComponent<SpriteRenderer>(); renderer.sortingOrder = 1;
            renderer.sharedMaterial = material; renderer.spriteSortPoint = SpriteSortPoint.Pivot;
            var character = ground.AddComponent<Sibir128Character>(); character.Configure(definition, pages, renderer, camera);
            ground.AddComponent<Sibir128Demo>(); Selection.activeGameObject = ground;
            Debug.Log("2D preview scene created additively. Play: move the mouse; Space toggles walking. Existing scenes were not saved or replaced.");
        }
    }
}
