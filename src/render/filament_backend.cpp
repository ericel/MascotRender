#include "render/filament_backend.hpp"

#include <backend/PixelBufferDescriptor.h>
#include <filament/Camera.h>
#include <filament/Engine.h>
#include <filament/LightManager.h>
#include <filament/Renderer.h>
#include <filament/Scene.h>
#include <filament/SwapChain.h>
#include <filament/View.h>
#include <filament/Viewport.h>
#include <gltfio/Animator.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/FilamentAsset.h>
#include <gltfio/FilamentInstance.h>
#include <gltfio/MaterialProvider.h>
#include <gltfio/ResourceLoader.h>
#include <utils/EntityManager.h>
#include <utils/NameComponentManager.h>

#include <algorithm>
#include <array>
#include <fstream>
#include <iterator>
#include <limits>
#include <memory>
#include <sstream>

namespace mascotrender::detail {
namespace {

constexpr std::size_t max_glb_bytes = 64U * 1024U * 1024U;
constexpr std::array<std::uint8_t, 4> glb_magic{'g', 'l', 'T', 'F'};
constexpr std::uint32_t min_render_extent = 16U;
constexpr std::uint32_t max_render_extent = 2048U;

struct EngineDeleter {
  void operator()(filament::Engine *engine) const noexcept {
    if (engine != nullptr) {
      filament::Engine::destroy(&engine);
    }
  }
};

struct MaterialProviderDeleter {
  void
  operator()(filament::gltfio::MaterialProvider *materials) const noexcept {
    if (materials != nullptr) {
      materials->destroyMaterials();
      delete materials;
    }
  }
};

struct AssetLoaderDeleter {
  void operator()(filament::gltfio::AssetLoader *loader) const noexcept {
    if (loader != nullptr) {
      filament::gltfio::AssetLoader::destroy(&loader);
    }
  }
};

struct AssetDeleter {
  filament::gltfio::AssetLoader *loader{};

  void operator()(filament::gltfio::FilamentAsset *asset) const noexcept {
    if (asset != nullptr) {
      loader->destroyAsset(asset);
    }
  }
};

struct FilamentRenderResources {
  filament::Engine *engine{};
  filament::SwapChain *swap_chain{};
  filament::Renderer *renderer{};
  filament::Scene *scene{};
  filament::View *view{};
  utils::Entity camera_entity{};
  utils::Entity light_entity{};

  ~FilamentRenderResources() {
    if (engine == nullptr) {
      return;
    }
    engine->flushAndWait();
    if (view != nullptr) {
      view->setCamera(nullptr);
      view->setScene(nullptr);
      engine->destroy(view);
    }
    if (scene != nullptr) {
      engine->destroy(scene);
    }
    if (renderer != nullptr) {
      engine->destroy(renderer);
    }
    if (swap_chain != nullptr) {
      engine->destroy(swap_chain);
    }
    auto &entities = utils::EntityManager::get();
    if (camera_entity) {
      engine->destroy(camera_entity);
      entities.destroy(camera_entity);
    }
    if (light_entity) {
      engine->destroy(light_entity);
      entities.destroy(light_entity);
    }
  }
};

[[nodiscard]] Result<std::vector<std::uint8_t>>
read_glb(const std::filesystem::path &path) {
  std::error_code size_error;
  const auto size = std::filesystem::file_size(path, size_error);
  if (size_error) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::io_error, "Cannot read GLB file size", path.string()});
  }
  if (size < 12U || size > max_glb_bytes ||
      size > std::numeric_limits<std::uint32_t>::max()) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::invalid_document,
              "GLB must be between 12 bytes and the 64 MiB safety limit",
              path.string()});
  }

  std::ifstream input{path, std::ios::binary};
  if (!input) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::io_error, "Cannot open GLB file", path.string()});
  }
  std::vector<std::uint8_t> bytes{std::istreambuf_iterator<char>{input},
                                  std::istreambuf_iterator<char>{}};
  if (bytes.size() != size ||
      !std::equal(glb_magic.begin(), glb_magic.end(), bytes.begin())) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::invalid_document, "File is not a GLB 2.0 document",
              path.string()});
  }
  if (bytes[4] != 2U || bytes[5] != 0U || bytes[6] != 0U || bytes[7] != 0U) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::invalid_document, "Only GLB version 2 is supported",
              path.string()});
  }
  return Result<std::vector<std::uint8_t>>::success(std::move(bytes));
}

} // namespace

Result<GlbAssetInfo>
inspect_filament_glb(const std::filesystem::path &path,
                     const std::vector<std::string> &required_anchors) {
  auto bytes = read_glb(path);
  if (!bytes) {
    return Result<GlbAssetInfo>::failure(bytes.error());
  }

  std::unique_ptr<filament::Engine, EngineDeleter> engine{
      filament::Engine::create()};
  if (!engine) {
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create a rendering engine", path.string()});
  }

  utils::NameComponentManager names{utils::EntityManager::get()};
  std::unique_ptr<filament::gltfio::MaterialProvider, MaterialProviderDeleter>
      materials{filament::gltfio::createJitShaderProvider(engine.get())};
  if (!materials) {
    return Result<GlbAssetInfo>::failure(Error{
        ErrorCode::renderer_initialization_failed,
        "Filament could not create a glTF material provider", path.string()});
  }

  filament::gltfio::AssetConfiguration configuration{};
  configuration.engine = engine.get();
  configuration.materials = materials.get();
  configuration.names = &names;
  std::unique_ptr<filament::gltfio::AssetLoader, AssetLoaderDeleter> loader{
      filament::gltfio::AssetLoader::create(configuration)};
  if (!loader) {
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create a GLB loader", path.string()});
  }

  auto *loaded = loader->createAsset(
      bytes.value().data(), static_cast<std::uint32_t>(bytes.value().size()));
  std::unique_ptr<filament::gltfio::FilamentAsset, AssetDeleter> asset{
      loaded, AssetDeleter{loader.get()}};
  if (!asset) {
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::invalid_document, "Filament rejected the GLB document",
              path.string()});
  }

  std::vector<std::string> missing;
  for (const auto &anchor : required_anchors) {
    if (anchor.empty() || !asset->getFirstEntityByName(anchor.c_str())) {
      missing.push_back(anchor.empty() ? "<empty>" : anchor);
    }
  }
  if (!missing.empty()) {
    std::ostringstream message;
    message << "GLB is missing required semantic anchor";
    if (missing.size() != 1U) {
      message << 's';
    }
    message << ": ";
    for (std::size_t index = 0; index < missing.size(); ++index) {
      if (index != 0U) {
        message << ", ";
      }
      message << missing[index];
    }
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::invalid_document, message.str(), path.string()});
  }

  std::size_t morph_targets = 0U;
  const auto *renderables = asset->getRenderableEntities();
  for (std::size_t index = 0; index < asset->getRenderableEntityCount();
       ++index) {
    morph_targets += asset->getMorphTargetCountAt(renderables[index]);
  }

  std::size_t animations = 0U;
  if (auto *instance = asset->getInstance(); instance != nullptr) {
    if (auto *animator = instance->getAnimator(); animator != nullptr) {
      animations = animator->getAnimationCount();
    }
  }

  return Result<GlbAssetInfo>::success(GlbAssetInfo{
      static_cast<std::uint32_t>(asset->getEntityCount()),
      static_cast<std::uint32_t>(asset->getRenderableEntityCount()),
      static_cast<std::uint32_t>(asset->getCameraEntityCount()),
      static_cast<std::uint32_t>(asset->getLightEntityCount()),
      static_cast<std::uint32_t>(animations),
      static_cast<std::uint32_t>(morph_targets), required_anchors});
}

Result<FilamentFrame>
render_filament_glb(const std::filesystem::path &path,
                    const FilamentRenderOptions &options) {
  if (options.width < min_render_extent || options.width > max_render_extent ||
      options.height < min_render_extent ||
      options.height > max_render_extent || options.vertical_span <= 0.0F) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::invalid_argument,
              "Filament output must be 16..2048 pixels with a positive span",
              path.string()});
  }

  auto bytes = read_glb(path);
  if (!bytes) {
    return Result<FilamentFrame>::failure(bytes.error());
  }

  std::unique_ptr<filament::Engine, EngineDeleter> engine{
      filament::Engine::create()};
  if (!engine) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create a rendering engine", path.string()});
  }

  utils::NameComponentManager names{utils::EntityManager::get()};
  std::unique_ptr<filament::gltfio::MaterialProvider, MaterialProviderDeleter>
      materials{filament::gltfio::createJitShaderProvider(engine.get())};
  if (!materials) {
    return Result<FilamentFrame>::failure(Error{
        ErrorCode::renderer_initialization_failed,
        "Filament could not create a glTF material provider", path.string()});
  }

  filament::gltfio::AssetConfiguration configuration{};
  configuration.engine = engine.get();
  configuration.materials = materials.get();
  configuration.names = &names;
  std::unique_ptr<filament::gltfio::AssetLoader, AssetLoaderDeleter> loader{
      filament::gltfio::AssetLoader::create(configuration)};
  if (!loader) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create a GLB loader", path.string()});
  }

  auto *loaded = loader->createAsset(
      bytes.value().data(), static_cast<std::uint32_t>(bytes.value().size()));
  std::unique_ptr<filament::gltfio::FilamentAsset, AssetDeleter> asset{
      loaded, AssetDeleter{loader.get()}};
  if (!asset) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::invalid_document, "Filament rejected the GLB document",
              path.string()});
  }

  const auto glb_path = path.string();
  filament::gltfio::ResourceLoader resources{
      {engine.get(), glb_path.c_str(), true}};
  if (!resources.loadResources(asset.get())) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::invalid_document,
              "Filament could not upload the GLB resources", path.string()});
  }
  asset->releaseSourceData();

  FilamentRenderResources render{engine.get()};
  render.swap_chain = engine->createSwapChain(options.width, options.height);
  render.renderer = engine->createRenderer();
  render.scene = engine->createScene();
  render.view = engine->createView();
  if (render.swap_chain == nullptr || render.renderer == nullptr ||
      render.scene == nullptr || render.view == nullptr) {
    return Result<FilamentFrame>::failure(Error{
        ErrorCode::renderer_initialization_failed,
        "Filament could not create the headless render target", path.string()});
  }

  auto &entities = utils::EntityManager::get();
  render.camera_entity = entities.create();
  auto *camera = engine->createCamera(render.camera_entity);
  if (camera == nullptr) {
    return Result<FilamentFrame>::failure(Error{
        ErrorCode::renderer_initialization_failed,
        "Filament could not create the orthographic camera", path.string()});
  }
  const auto aspect =
      static_cast<double>(options.width) / static_cast<double>(options.height);
  const auto half_height = static_cast<double>(options.vertical_span) * 0.5;
  const auto half_width = half_height * aspect;
  camera->setProjection(filament::Camera::Projection::ORTHO, -half_width,
                        half_width, -half_height, half_height, 0.1, 100.0);
  camera->lookAt({0.0, 0.0, 4.0}, {0.0, 0.0, 0.0}, {0.0, 1.0, 0.0});
  camera->setExposure(16.0F, 1.0F / 125.0F, 100.0F);

  render.light_entity = entities.create();
  const auto light_result =
      filament::LightManager::Builder{filament::LightManager::Type::DIRECTIONAL}
          .direction({0.304F, -0.391F, -0.868F})
          .color({1.0F, 0.92F, 0.82F})
          .intensity(65000.0F)
          .castShadows(false)
          .build(*engine, render.light_entity);
  if (light_result != filament::LightManager::Builder::Success) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create the toon key light", path.string()});
  }

  render.scene->addEntities(asset->getEntities(), asset->getEntityCount());
  render.scene->addEntity(render.light_entity);
  render.view->setScene(render.scene);
  render.view->setCamera(camera);
  render.view->setViewport({0, 0, options.width, options.height});
  render.view->setBlendMode(filament::View::BlendMode::TRANSLUCENT);
  render.view->setPostProcessingEnabled(false);
  render.view->setAntiAliasing(filament::View::AntiAliasing::NONE);
  render.view->setDithering(filament::View::Dithering::NONE);
  filament::Renderer::ClearOptions clear_options{};
  clear_options.clearColor = {0.0, 0.0, 0.0, 0.0};
  clear_options.clear = true;
  clear_options.discard = true;
  render.renderer->setClearOptions(clear_options);

  FilamentFrame frame{options.width, options.height,
                      std::vector<std::uint8_t>(
                          static_cast<std::size_t>(options.width) *
                              static_cast<std::size_t>(options.height) * 4U,
                          0U)};
  if (!render.renderer->beginFrame(render.swap_chain)) {
    return Result<FilamentFrame>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament skipped the headless render frame", path.string()});
  }
  render.renderer->render(render.view);
  render.renderer->readPixels(0, 0, options.width, options.height,
                              filament::backend::PixelBufferDescriptor{
                                  frame.rgba.data(), frame.rgba.size(),
                                  filament::backend::PixelDataFormat::RGBA,
                                  filament::backend::PixelDataType::UBYTE});
  render.renderer->endFrame();
  engine->flushAndWait();
  return Result<FilamentFrame>::success(std::move(frame));
}

} // namespace mascotrender::detail
