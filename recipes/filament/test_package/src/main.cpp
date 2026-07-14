#include <filament/Engine.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/MaterialProvider.h>

int main() {
#if defined(_WIN32)
  // GitHub's Windows runner has no Vulkan ICD. NOOP still exercises the
  // packaged Filament runtime without pretending that it rendered pixels.
  auto *engine =
      filament::Engine::create(filament::Engine::Backend::NOOP);
#else
  auto *engine = filament::Engine::create();
#endif
  if (engine == nullptr) {
    return 1;
  }

  auto *materials = filament::gltfio::createJitShaderProvider(engine);
  if (materials == nullptr) {
    filament::Engine::destroy(&engine);
    return 2;
  }

  auto *loader = filament::gltfio::AssetLoader::create({engine, materials});
  if (loader == nullptr) {
    materials->destroyMaterials();
    delete materials;
    filament::Engine::destroy(&engine);
    return 3;
  }

  filament::gltfio::AssetLoader::destroy(&loader);
  materials->destroyMaterials();
  delete materials;
  filament::Engine::destroy(&engine);
  return 0;
}
