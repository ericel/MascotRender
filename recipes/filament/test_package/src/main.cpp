#include <filament/Engine.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/MaterialProvider.h>

int main() {
  auto *engine = filament::Engine::create();
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
