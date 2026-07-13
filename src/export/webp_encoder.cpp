#include "export/webp_encoder.hpp"

#include <cstring>
#include <string>

#include <webp/encode.h>

namespace mascotrender::detail {
namespace {

[[nodiscard]] Error encode_error(std::string message) {
    return Error{ErrorCode::encode_failed, std::move(message)};
}

}  // namespace

Result<EncodedImage> encode_webp(
    const PixelBuffer& pixels, const RenderOptions& options) {
    WebPConfig config;
    if (WebPConfigInit(&config) == 0) {
        return Result<EncodedImage>::failure(
            encode_error("libwebp configuration initialization failed"));
    }
    config.lossless = options.lossless ? 1 : 0;
    config.quality = options.webp_quality;
    // Method 4 is deterministic and gives a practical quality/throughput balance.
    // Method 6 was measured at several seconds for this small 512 px scene.
    config.method = 4;
    config.exact = 1;
    config.thread_level = 0;
    if (WebPValidateConfig(&config) == 0) {
        return Result<EncodedImage>::failure(
            encode_error("Invalid libwebp encoding configuration"));
    }

    WebPPicture picture;
    if (WebPPictureInit(&picture) == 0) {
        return Result<EncodedImage>::failure(
            encode_error("libwebp picture initialization failed"));
    }
    picture.use_argb = 1;
    picture.width = static_cast<int>(pixels.width);
    picture.height = static_cast<int>(pixels.height);

    WebPMemoryWriter writer;
    WebPMemoryWriterInit(&writer);
    picture.writer = WebPMemoryWrite;
    picture.custom_ptr = &writer;

    const auto* bytes = reinterpret_cast<const std::uint8_t*>(pixels.pixels.data());
    const bool imported =
        WebPPictureImportBGRA(&picture, bytes, static_cast<int>(pixels.stride_bytes)) != 0;
    const bool encoded = imported && WebPEncode(&config, &picture) != 0;

    EncodedImage output;
    if (encoded) {
        output.width = pixels.width;
        output.height = pixels.height;
        output.bytes.resize(writer.size);
        std::memcpy(output.bytes.data(), writer.mem, writer.size);
    }

    WebPPictureFree(&picture);
    WebPMemoryWriterClear(&writer);

    if (!encoded) {
        return Result<EncodedImage>::failure(
            encode_error(imported ? "libwebp encoding failed"
                                  : "libwebp could not import the BGRA buffer"));
    }
    return Result<EncodedImage>::success(std::move(output));
}

}  // namespace mascotrender::detail
