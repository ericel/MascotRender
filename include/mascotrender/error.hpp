#pragma once

#include <string>
#include <utility>

namespace mascotrender {

enum class ErrorCode {
    invalid_argument,
    io_error,
    invalid_document,
    renderer_initialization_failed,
    render_failed,
    encode_failed,
};

struct Error {
    Error() = default;

    Error(ErrorCode error_code, std::string error_message,
          std::string error_source = {}, std::string error_location = {})
        : code{error_code},
          message{std::move(error_message)},
          source{std::move(error_source)},
          location{std::move(error_location)} {}

    ErrorCode code{};
    std::string message;
    std::string source;
    std::string location;
};

}  // namespace mascotrender
