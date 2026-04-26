"""
Probe whether hevc_cuvid actually works in PyAV and what the
CodecContext API looks like in the installed version.

Run with:
  python scripts/dev/probe_nvdec.py [path/to/test_video.mp4]
"""
import sys

try:
    import av
except ImportError:
    print("PyAV not installed. Run: conda install -c conda-forge av")
    sys.exit(1)

print(f"PyAV version: {av.__version__}")
print()

# --- codec availability ---
cuvid = sorted(c for c in av.codec.codecs_available if c.endswith("_cuvid"))
print(f"cuvid codecs in this FFmpeg build ({len(cuvid)}):")
for c in cuvid:
    print(f"  {c}")
print()

# --- try to instantiate hevc_cuvid directly ---
hw = "hevc_cuvid"
print(f"Testing direct instantiation of {hw!r}...")
try:
    codec_obj = av.codec.Codec(hw, "r")
    print(f"  av.codec.Codec('{hw}', 'r') OK -> {codec_obj}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    codec_obj = None

print()
print("CodecContext.create exists:", hasattr(av.codec.CodecContext, "create"))

if codec_obj is not None:
    print("Trying CodecContext.create(codec_obj)...")
    try:
        ctx = av.codec.CodecContext.create(codec_obj)
        print(f"  OK: {ctx}")
        print(f"  ctx.name: {getattr(ctx, 'name', 'N/A')}")
        print(f"  ctx.type: {getattr(ctx, 'type', 'N/A')}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")

# --- try opening a real video if provided ---
if len(sys.argv) > 1:
    path = sys.argv[1]
    print()
    print(f"Testing actual decode of: {path}")
    import time

    # Software open to probe codec name
    with av.open(path) as probe:
        vs = probe.streams.video[0]
        codec_name = vs.codec_context.name
        w = vs.codec_context.width
        h = vs.codec_context.height
        fps = float(vs.average_rate or 30)
    print(f"  Source codec: {codec_name}, {w}x{h}, {fps:.1f}fps")

    hw_name = f"{codec_name}_cuvid"
    if hw_name not in cuvid:
        print(f"  {hw_name} not in available cuvid codecs — cannot test HW decode")
    else:
        # Method 1: open with codec= kwarg (PyAV >= 9 on some builds)
        print(f"\n  Method 1: av.open(..., codec={{video: '{hw_name}'}})")
        try:
            t0 = time.perf_counter()
            with av.open(path) as c:
                vs = c.streams.video[0]
                vs.codec_context = av.codec.CodecContext.create(av.codec.Codec(hw_name, "r"))
                vs.codec_context.open()
                actual = getattr(vs.codec_context, "name", "?")
                print(f"    codec context name after force: {actual!r}")
                # decode first keyframe
                for pkt in c.demux(vs):
                    if pkt.is_keyframe:
                        frames = list(vs.codec_context.decode(pkt))
                        print(f"    decoded {len(frames)} frame(s) from first keyframe")
                        if frames:
                            f = frames[0]
                            print(f"    frame format: {f.format}, size: {f.width}x{f.height}")
                        break
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"    Time: {elapsed:.0f}ms")
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {e}")

print()
print("Done.")
