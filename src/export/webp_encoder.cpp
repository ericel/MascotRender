#include "export/webp_encoder.hpp"

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include <webp/encode.h>
#include <webp/mux.h>

namespace mascotrender::detail {
namespace {

[[nodiscard]] Error encode_error(std::string message) {
    return Error{ErrorCode::encode_failed, std::move(message)};
}

[[nodiscard]] bool configure(WebPConfig& config, const RenderOptions& options) {
    if (WebPConfigInit(&config) == 0) {
        return false;
    }
    config.lossless = options.lossless ? 1 : 0;
    config.quality = options.webp_quality;
    config.method = 4;
    config.exact = 1;
    config.thread_level = 0;
    return WebPValidateConfig(&config) != 0;
}

}  // namespace

Result<EncodedImage> encode_webp(const PixelBuffer& pixels,
                                 const RenderOptions& options) {
    WebPConfig config;
    // Method 4 is deterministic and gives a practical quality/throughput
    // balance. Method 6 was measured at several seconds for this small 512 px
    // scene.
    if (!configure(config, options)) {
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

    const auto* bytes =
        reinterpret_cast<const std::uint8_t*>(pixels.pixels.data());
    const bool imported =
        WebPPictureImportBGRA(&picture, bytes,
                              static_cast<int>(pixels.stride_bytes)) != 0;
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
        return Result<EncodedImage>::failure(encode_error(
            imported ? "libwebp encoding failed"
                     : "libwebp could not import the BGRA buffer"));
    }
    return Result<EncodedImage>::success(std::move(output));
}

Result<EncodedImage> encode_animated_webp(
    const std::vector<AnimationFrame>& frames, std::uint32_t duration_ms,
    std::uint32_t loop_count, const RenderOptions& options) {
    if (frames.size() < 2U || frames.front().pixels.width == 0U ||
        frames.front().pixels.height == 0U || duration_ms == 0U) {
        return Result<EncodedImage>::failure(
            encode_error("Animated WebP requires at least two valid frames"));
    }

    WebPConfig config;
    if (!configure(config, options)) {
        return Result<EncodedImage>::failure(
            encode_error("Invalid animated WebP configuration"));
    }

    WebPAnimEncoderOptions encoder_options;
    if (WebPAnimEncoderOptionsInit(&encoder_options) == 0) {
        return Result<EncodedImage>::failure(
            encode_error("Animated WebP option initialization failed"));
    }
    encoder_options.anim_params.bgcolor = 0U;
    encoder_options.anim_params.loop_count = static_cast<int>(loop_count);
    encoder_options.minimize_size = 0;
    encoder_options.kmin = 0;
    encoder_options.kmax = 0;
    encoder_options.allow_mixed = 0;
    encoder_options.verbose = 0;

    const auto width = frames.front().pixels.width;
    const auto height = frames.front().pixels.height;
    auto* encoder = WebPAnimEncoderNew(
        static_cast<int>(width), static_cast<int>(height), &encoder_options);
    if (encoder == nullptr) {
        return Result<EncodedImage>::failure(
            encode_error("Could not allocate animated WebP encoder"));
    }

    bool encoded = true;
    std::string failure;
    std::uint32_t previous_timestamp = 0U;
    for (std::size_t index = 0; index < frames.size(); ++index) {
        const auto& frame = frames[index];
        if (frame.pixels.width != width || frame.pixels.height != height ||
            (index != 0U && frame.timestamp_ms <= previous_timestamp) ||
            frame.timestamp_ms >= duration_ms) {
            encoded = false;
            failure =
                "Animated WebP frames have inconsistent dimensions or "
                "timestamps";
            break;
        }

        WebPPicture picture;
        if (WebPPictureInit(&picture) == 0) {
            encoded = false;
            failure = "Animated WebP picture initialization failed";
            break;
        }
        picture.use_argb = 1;
        picture.width = static_cast<int>(width);
        picture.height = static_cast<int>(height);
        const auto* bytes =
            reinterpret_cast<const std::uint8_t*>(frame.pixels.pixels.data());
        const auto imported = WebPPictureImportBGRA(
            &picture, bytes, static_cast<int>(frame.pixels.stride_bytes));
        const auto added =
            imported != 0 &&
            WebPAnimEncoderAdd(encoder, &picture,
                               static_cast<int>(frame.timestamp_ms),
                               &config) != 0;
        WebPPictureFree(&picture);
        if (!added) {
            encoded = false;
            const auto* error = WebPAnimEncoderGetError(encoder);
            failure = imported == 0 ? "Could not import animated WebP frame"
                                    : (error == nullptr
                                           ? "Could not add animated WebP frame"
                                           : error);
            break;
        }
        previous_timestamp = frame.timestamp_ms;
    }

    if (encoded &&
        WebPAnimEncoderAdd(encoder, nullptr, static_cast<int>(duration_ms),
                           nullptr) == 0) {
        encoded = false;
        const auto* error = WebPAnimEncoderGetError(encoder);
        failure = error == nullptr ? "Could not finalize animated WebP timeline"
                                   : error;
    }

    WebPData assembled;
    WebPDataInit(&assembled);
    if (encoded && WebPAnimEncoderAssemble(encoder, &assembled) == 0) {
        encoded = false;
        const auto* error = WebPAnimEncoderGetError(encoder);
        failure = error == nullptr ? "Could not assemble animated WebP" : error;
    }

    EncodedImage output;
    if (encoded) {
        output.width = width;
        output.height = height;
        output.bytes.resize(assembled.size);
        std::memcpy(output.bytes.data(), assembled.bytes, assembled.size);
    }
    WebPDataClear(&assembled);
    WebPAnimEncoderDelete(encoder);

    if (!encoded) {
        return Result<EncodedImage>::failure(encode_error(
            failure.empty() ? "Animated WebP encoding failed" : failure));
    }
    return Result<EncodedImage>::success(std::move(output));
}

}  // namespace mascotrender::detail
