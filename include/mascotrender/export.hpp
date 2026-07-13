#pragma once

#if defined(_WIN32) && defined(MASCOTRENDER_SHARED)
#    if defined(MASCOTRENDER_BUILDING_LIBRARY)
#        define MASCOTRENDER_API __declspec(dllexport)
#    else
#        define MASCOTRENDER_API __declspec(dllimport)
#    endif
#elif defined(MASCOTRENDER_SHARED) && defined(__GNUC__)
#    define MASCOTRENDER_API __attribute__((visibility("default")))
#else
#    define MASCOTRENDER_API
#endif
