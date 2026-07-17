#include "render/thorvg_backend.hpp"

#include <thorvg.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "render/caption_layout.hpp"

namespace mascotrender::detail {
namespace {

[[nodiscard]] Error render_error(std::string message) {
  return Error{ErrorCode::render_failed, std::move(message)};
}

[[nodiscard]] bool succeeded(tvg::Result result) {
  return result == tvg::Result::Success;
}

[[nodiscard]] AffineTransform multiply(const AffineTransform &left,
                                       const AffineTransform &right) {
  return AffineTransform{left.m11 * right.m11 + left.m12 * right.m21,
                         left.m11 * right.m12 + left.m12 * right.m22,
                         left.m21 * right.m11 + left.m22 * right.m21,
                         left.m21 * right.m12 + left.m22 * right.m22,
                         left.m11 * right.translate_x +
                             left.m12 * right.translate_y + left.translate_x,
                         left.m21 * right.translate_x +
                             left.m22 * right.translate_y + left.translate_y};
}

[[nodiscard]] bool is_identity(const AffineTransform &transform) {
  return transform.m11 == 1.0F && transform.m12 == 0.0F &&
         transform.m21 == 0.0F && transform.m22 == 1.0F &&
         transform.translate_x == 0.0F && transform.translate_y == 0.0F;
}

[[nodiscard]] tvg::Matrix thorvg_matrix(const AffineTransform &transform) {
  return tvg::Matrix{transform.m11, transform.m12, transform.translate_x,
                     transform.m21, transform.m22, transform.translate_y,
                     0.0F,          0.0F,          1.0F};
}

[[nodiscard]] AffineTransform animation_transform(const NodeFrameState &state,
                                                  const Point &pivot) {
  constexpr float degrees_to_radians = 3.14159265358979323846F / 180.0F;
  const auto angle = state.rotation_degrees * degrees_to_radians;
  const auto cosine = std::cos(angle);
  const auto sine = std::sin(angle);
  const auto m11 = cosine * state.scale_x;
  const auto m12 = -sine * state.scale_y;
  const auto m21 = sine * state.scale_x;
  const auto m22 = cosine * state.scale_y;
  return AffineTransform{
      m11,
      m12,
      m21,
      m22,
      state.translate_x + pivot.x - m11 * pivot.x - m12 * pivot.y,
      state.translate_y + pivot.y - m21 * pivot.x - m22 * pivot.y};
}

[[nodiscard]] std::unique_ptr<tvg::Shape>
circle(float cx, float cy, float rx, float ry, std::uint8_t red,
       std::uint8_t green, std::uint8_t blue, std::uint8_t alpha = 255) {
  auto shape = tvg::Shape::gen();
  if (!shape || !succeeded(shape->appendCircle(cx, cy, rx, ry)) ||
      !succeeded(shape->fill(red, green, blue, alpha))) {
    return nullptr;
  }
  return shape;
}

[[nodiscard]] std::unique_ptr<tvg::Shape>
rounded_rect(float x, float y, float width, float height, float radius,
             std::uint8_t red, std::uint8_t green, std::uint8_t blue,
             std::uint8_t alpha = 255) {
  auto shape = tvg::Shape::gen();
  if (!shape ||
      !succeeded(shape->appendRect(x, y, width, height, radius, radius)) ||
      !succeeded(shape->fill(red, green, blue, alpha))) {
    return nullptr;
  }
  return shape;
}

[[nodiscard]] std::unique_ptr<tvg::Shape>
triangle(float x1, float y1, float x2, float y2, float x3, float y3,
         std::uint8_t red, std::uint8_t green, std::uint8_t blue) {
  auto shape = tvg::Shape::gen();
  if (!shape || !succeeded(shape->moveTo(x1, y1)) ||
      !succeeded(shape->lineTo(x2, y2)) || !succeeded(shape->lineTo(x3, y3)) ||
      !succeeded(shape->close()) || !succeeded(shape->fill(red, green, blue))) {
    return nullptr;
  }
  return shape;
}

[[nodiscard]] bool push(tvg::SwCanvas &canvas,
                        std::unique_ptr<tvg::Paint> paint) {
  return paint && succeeded(canvas.push(std::move(paint)));
}

[[nodiscard]] std::unique_ptr<tvg::Text>
make_text(const TextBlock &block, const std::string &line, float font_size,
          const Color &color, TextMetrics *metrics = nullptr) {
  auto text = tvg::Text::gen();
  const auto font_key = block.font.string();
  if (!text || !succeeded(text->font(font_key.c_str(), font_size)) ||
      !succeeded(text->text(line.c_str())) ||
      !succeeded(text->fill(color.red, color.green, color.blue))) {
    return nullptr;
  }
  if (metrics &&
      !succeeded(text->bounds(&metrics->x, &metrics->y, &metrics->width,
                              &metrics->height, false))) {
    return nullptr;
  }
  return text;
}

[[nodiscard]] bool position_text(tvg::Text &text, float x, float y,
                                 const Rect &area, const FrameState &frame) {
  if (frame.text_scale == 1.0F && frame.text_rotation_degrees == 0.0F) {
    if (!succeeded(text.translate(x + frame.text_translate_x,
                                  y + frame.text_translate_y))) {
      return false;
    }
  } else {
    const auto center_x = area.x + area.width * 0.5F;
    const auto center_y = area.y + area.height * 0.5F;
    const auto radians = frame.text_rotation_degrees *
                         3.14159265358979323846F / 180.0F;
    const auto cosine = std::cos(radians);
    const auto sine = std::sin(radians);
    const auto m11 = frame.text_scale * cosine;
    const auto m12 = -frame.text_scale * sine;
    const auto m21 = frame.text_scale * sine;
    const auto m22 = frame.text_scale * cosine;
    const tvg::Matrix transform{
        m11,
        m12,
        m11 * x + m12 * y + center_x - m11 * center_x -
            m12 * center_y + frame.text_translate_x,
        m21,
        m22,
        m21 * x + m22 * y + center_y - m21 * center_x -
            m22 * center_y + frame.text_translate_y,
        0.0F,
        0.0F,
        1.0F};
    if (!succeeded(text.transform(transform))) {
      return false;
    }
  }
  const auto opacity = static_cast<std::uint8_t>(
      std::lround(std::clamp(frame.text_opacity, 0.0F, 1.0F) * 255.0F));
  return opacity == 255U || succeeded(text.opacity(opacity));
}

[[nodiscard]] std::optional<Error> push_text(tvg::SwCanvas &canvas,
                                             const TextBlock &block,
                                             float scale_x, float scale_y,
                                             const FrameState &frame) {
  const auto font_key = block.font.string();
  if (!succeeded(tvg::Text::load(font_key))) {
    return render_error("ThorVG could not load TTF font: " + font_key);
  }

  const auto measure = [&block](std::string_view line,
                                float font_size) -> std::optional<TextMetrics> {
    TextMetrics metrics;
    if (!make_text(block, std::string{line}, font_size, block.fill, &metrics)) {
      return std::nullopt;
    }
    return metrics;
  };

  auto resolved = resolve_caption(block, scale_x, scale_y, measure);
  if (!resolved) {
    return render_error("Sticker text does not fit any candidate area at the "
                        "minimum font size");
  }
  const auto &area = resolved->area;
  const auto &fitted = resolved->fitted;
  const auto outline_width = resolved->outline_width;
  for (std::size_t index = 0; index < fitted.lines.size(); ++index) {
    const auto x = resolved->positions[index].x;
    const auto y = resolved->positions[index].y;
    if (outline_width > 0.0F) {
      constexpr float diagonal = 0.70710678118F;
      const std::pair<float, float> offsets[] = {
          {-outline_width, 0.0F},
          {outline_width, 0.0F},
          {0.0F, -outline_width},
          {0.0F, outline_width},
          {-outline_width * diagonal, -outline_width * diagonal},
          {outline_width * diagonal, -outline_width * diagonal},
          {-outline_width * diagonal, outline_width * diagonal},
          {outline_width * diagonal, outline_width * diagonal}};
      for (const auto &[offset_x, offset_y] : offsets) {
        auto outline = make_text(block, fitted.lines[index], fitted.font_size,
                                 block.outline, nullptr);
        if (!outline ||
            !position_text(*outline, x + offset_x, y + offset_y, area, frame) ||
            !push(canvas, std::move(outline))) {
          return render_error("ThorVG could not construct text outline");
        }
      }
    }
    auto text = make_text(block, fitted.lines[index], fitted.font_size,
                          block.fill, nullptr);
    if (!text || !position_text(*text, x, y, area, frame) ||
        !push(canvas, std::move(text))) {
      return render_error("ThorVG could not position sticker text");
    }
  }
  return std::nullopt;
}

[[nodiscard]] PixelBuffer copy_target(const std::vector<std::uint32_t> &target,
                                      std::uint32_t width,
                                      std::uint32_t height) {
  PixelBuffer output;
  output.width = width;
  output.height = height;
  output.stride_bytes = width * 4U;
  output.pixels.resize(static_cast<std::size_t>(output.stride_bytes) * height);

  // ThorVG's ARGB8888S is a numeric AARRGGBB value. Extracting channels
  // explicitly makes the public BGRA byte layout independent of host
  // endianness.
  for (std::size_t index = 0; index < target.size(); ++index) {
    const auto pixel = target[index];
    const auto offset = index * 4U;
    output.pixels[offset] = static_cast<std::byte>(pixel & 0xffU);
    output.pixels[offset + 1U] = static_cast<std::byte>((pixel >> 8U) & 0xffU);
    output.pixels[offset + 2U] = static_cast<std::byte>((pixel >> 16U) & 0xffU);
    output.pixels[offset + 3U] = static_cast<std::byte>((pixel >> 24U) & 0xffU);
  }
  return output;
}

} // namespace

ThorvgBackend::ThorvgBackend() {
  const auto result = tvg::Initializer::init(tvg::CanvasEngine::Sw, 0);
  if (!succeeded(result)) {
    initialization_error_ =
        Error{ErrorCode::renderer_initialization_failed,
              "ThorVG software renderer initialization failed"};
  }
}

ThorvgBackend::~ThorvgBackend() {
  if (!initialization_error_) {
    static_cast<void>(tvg::Initializer::term(tvg::CanvasEngine::Sw));
  }
}

Result<PixelBuffer> ThorvgBackend::render_sample(std::uint32_t width,
                                                 std::uint32_t height) const {
  if (initialization_error_) {
    return Result<PixelBuffer>::failure(*initialization_error_);
  }
  if (width == 0 || height == 0 ||
      static_cast<std::uint64_t>(width) * height >
          std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t)) {
    return Result<PixelBuffer>::failure(
        render_error("Invalid or unsupported render dimensions"));
  }

  std::vector<std::uint32_t> target(static_cast<std::size_t>(width) * height,
                                    0U);
  auto canvas = tvg::SwCanvas::gen();
  if (!canvas) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG could not allocate a software canvas"));
  }
  if (!succeeded(canvas->mempool(tvg::SwCanvas::MempoolPolicy::Individual)) ||
      !succeeded(canvas->target(target.data(), width, width, height,
                                tvg::SwCanvas::ARGB8888S))) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG could not configure the render target"));
  }

  const float sx = static_cast<float>(width) / 512.0F;
  const float sy = static_cast<float>(height) / 512.0F;
  const auto px = [sx](float value) { return value * sx; };
  const auto py = [sy](float value) { return value * sy; };

  // A small deterministic mascot scene. The transparent canvas is
  // intentional.
  if (!push(*canvas,
            circle(px(264), py(420), px(154), py(28), 32, 45, 72, 48)) ||
      !push(*canvas, triangle(px(142), py(180), px(185), py(73), px(235),
                              py(176), 243, 139, 55)) ||
      !push(*canvas, triangle(px(277), py(176), px(327), py(73), px(370),
                              py(180), 243, 139, 55)) ||
      !push(*canvas, rounded_rect(px(123), py(145), px(266), py(272), px(112),
                                  247, 155, 67)) ||
      !push(*canvas, circle(px(209), py(257), px(24), py(31), 35, 48, 70)) ||
      !push(*canvas, circle(px(303), py(257), px(24), py(31), 35, 48, 70)) ||
      !push(*canvas, circle(px(216), py(248), px(7), py(9), 255, 255, 255)) ||
      !push(*canvas, circle(px(310), py(248), px(7), py(9), 255, 255, 255)) ||
      !push(*canvas, triangle(px(241), py(306), px(271), py(306), px(256),
                              py(323), 214, 90, 94)) ||
      !push(*canvas, circle(px(256), py(350), px(48), py(24), 255, 231, 205))) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG could not construct the sample scene"));
  }

  if (!succeeded(canvas->draw()) || !succeeded(canvas->sync())) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG failed while drawing the sample scene"));
  }

  return Result<PixelBuffer>::success(copy_target(target, width, height));
}

Result<PixelBuffer> ThorvgBackend::render_scene(const Scene &scene,
                                                std::uint32_t width,
                                                std::uint32_t height,
                                                const FrameState &frame) const {
  if (initialization_error_) {
    return Result<PixelBuffer>::failure(*initialization_error_);
  }
  if (scene.layers.empty() || scene.width == 0 || scene.height == 0 ||
      width == 0 || height == 0 ||
      static_cast<std::uint64_t>(width) * height >
          std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t)) {
    return Result<PixelBuffer>::failure(
        render_error("Invalid layer scene or render dimensions"));
  }

  std::vector<std::uint32_t> target(static_cast<std::size_t>(width) * height,
                                    0U);
  auto canvas = tvg::SwCanvas::gen();
  if (!canvas ||
      !succeeded(canvas->mempool(tvg::SwCanvas::MempoolPolicy::Individual)) ||
      !succeeded(canvas->target(target.data(), width, width, height,
                                tvg::SwCanvas::ARGB8888S))) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG could not configure the SVG render target"));
  }

  const auto scale_x =
      static_cast<float>(width) / static_cast<float>(scene.width);
  const auto scale_y =
      static_cast<float>(height) / static_cast<float>(scene.height);
  const auto animated_mascot =
      frame.mascot_scale != 1.0F || frame.mascot_offset_y != 0.0F;
  const AffineTransform output_scale{scale_x, 0.0F, 0.0F, scale_y, 0.0F, 0.0F};
  const auto center_x = static_cast<float>(scene.width) * 0.5F;
  const auto center_y = static_cast<float>(scene.height) * 0.5F;
  const AffineTransform mascot_transform{
      frame.mascot_scale,
      0.0F,
      0.0F,
      frame.mascot_scale,
      (1.0F - frame.mascot_scale) * center_x,
      (1.0F - frame.mascot_scale) * center_y + frame.mascot_offset_y};
  for (const auto &layer : scene.layers) {
    auto source = layer.source;
    const auto output_dimension = std::max(width, height);
    const auto lod = std::find_if(
        layer.lod_sources.begin(), layer.lod_sources.end(),
        [output_dimension](const auto &candidate) {
          return output_dimension <= candidate.first;
        });
    if (lod != layer.lod_sources.end()) {
      source = lod->second;
    }
    auto picture = tvg::Picture::gen();
    if (!picture || !succeeded(picture->load(source.string()))) {
      return Result<PixelBuffer>::failure(render_error(
          "ThorVG could not load SVG layer: " + source.string()));
    }
    auto visual_transform = layer.transform;
    auto animated_opacity = layer.opacity;
    for (auto node = layer.animation_chain.rbegin();
         node != layer.animation_chain.rend(); ++node) {
      const auto state = std::find_if(
          frame.nodes.begin(), frame.nodes.end(),
          [&node](const auto &item) { return item.target == node->id; });
      if (state != frame.nodes.end()) {
        visual_transform = multiply(animation_transform(*state, node->pivot),
                                    visual_transform);
        animated_opacity *= state->opacity;
      }
    }
    if (!layer.screen_space) {
      visual_transform.translate_x -=
          (scene.view_offset_x + frame.view_offset_x) * layer.depth;
      visual_transform.translate_y -=
          (scene.view_offset_y + frame.view_offset_y) * layer.depth;
    }
    if (animated_mascot && !layer.screen_space) {
      visual_transform = multiply(mascot_transform, visual_transform);
    }
    if (!layer.screen_space) {
      visual_transform = multiply(scene.camera_transform, visual_transform);
    }
    if (!is_identity(visual_transform)) {
      const auto transform = multiply(output_scale, visual_transform);
      if (!succeeded(picture->transform(thorvg_matrix(transform)))) {
        return Result<PixelBuffer>::failure(render_error(
            "ThorVG could not transform SVG layer: " + source.string()));
      }
    } else if (!succeeded(picture->size(static_cast<float>(width),
                                        static_cast<float>(height)))) {
      return Result<PixelBuffer>::failure(render_error(
          "ThorVG could not size SVG layer: " + source.string()));
    }
    const auto opacity = static_cast<std::uint8_t>(
        std::lround(std::clamp(animated_opacity, 0.0F, 1.0F) * 255.0F));
    if (opacity != 255U && !succeeded(picture->opacity(opacity))) {
      return Result<PixelBuffer>::failure(
          render_error("ThorVG could not apply SVG layer opacity: " +
                       source.string()));
    }
    if (!push(*canvas, std::move(picture))) {
      return Result<PixelBuffer>::failure(render_error(
          "ThorVG could not queue SVG layer: " + source.string()));
    }
  }

  for (const auto &text : scene.text) {
    if (auto error = push_text(*canvas, text, scale_x, scale_y, frame)) {
      return Result<PixelBuffer>::failure(std::move(*error));
    }
  }

  if (!succeeded(canvas->draw()) || !succeeded(canvas->sync())) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG failed while drawing SVG layers"));
  }
  return Result<PixelBuffer>::success(copy_target(target, width, height));
}

Result<PixelBuffer> ThorvgBackend::render_caption_overlay(
    const Scene &scene, std::uint32_t width, std::uint32_t height,
    const FrameState &frame) const {
  if (initialization_error_) {
    return Result<PixelBuffer>::failure(*initialization_error_);
  }
  if (scene.width == 0U || scene.height == 0U || width == 0U || height == 0U ||
      static_cast<std::uint64_t>(width) * height >
          std::numeric_limits<std::size_t>::max() / sizeof(std::uint32_t)) {
    return Result<PixelBuffer>::failure(
        render_error("Invalid caption scene or render dimensions"));
  }

  std::vector<std::uint32_t> target(static_cast<std::size_t>(width) * height,
                                    0U);
  auto canvas = tvg::SwCanvas::gen();
  if (!canvas ||
      !succeeded(canvas->mempool(tvg::SwCanvas::MempoolPolicy::Individual)) ||
      !succeeded(canvas->target(target.data(), width, width, height,
                                tvg::SwCanvas::ARGB8888S))) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG could not configure the caption render target"));
  }

  const auto scale_x =
      static_cast<float>(width) / static_cast<float>(scene.width);
  const auto scale_y =
      static_cast<float>(height) / static_cast<float>(scene.height);
  for (const auto &text : scene.text) {
    if (auto error = push_text(*canvas, text, scale_x, scale_y, frame)) {
      return Result<PixelBuffer>::failure(std::move(*error));
    }
  }
  if (!succeeded(canvas->draw()) || !succeeded(canvas->sync())) {
    return Result<PixelBuffer>::failure(
        render_error("ThorVG failed while drawing the caption overlay"));
  }
  return Result<PixelBuffer>::success(copy_target(target, width, height));
}

Result<PixelBuffer> ThorvgBackend::render_layer_overlay(
    const Scene &scene, const std::string &layer_id, std::uint32_t width,
    std::uint32_t height) const {
  Scene overlay = scene;
  std::erase_if(overlay.layers, [&layer_id](const auto &layer) {
    return layer.id != layer_id;
  });
  overlay.text.clear();
  overlay.view_offset_x = 0.0F;
  overlay.view_offset_y = 0.0F;
  if (overlay.layers.empty()) {
    return Result<PixelBuffer>::failure(render_error(
        "Screen-space overlay layer is not selected: " + layer_id));
  }
  return render_scene(overlay, width, height, {});
}

} // namespace mascotrender::detail
