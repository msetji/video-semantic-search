// About page — explains the project, the tech stack, and the team

export function About() {
    return (
        <main className="mx-auto max-w-4xl px-4 py-12 space-y-10 text-zinc-300">

            {/* Project overview */}
            <section>
                <h2 className="text-2xl font-semibold text-white mb-3">What is this?</h2>
                <p className="text-zinc-400 leading-relaxed">
                    Semantic Local Media Search lets you search your personal photo and video library
                    using plain English — no tags, no filenames, no cloud uploads required. Everything
                    runs locally on your machine.
                </p>
            </section>

            {/* How it works */}
            <section>
                <h2 className="text-2xl font-semibold text-white mb-4">How it works</h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-4">
                        <p className="text-violet-400 font-semibold mb-1">Step 1 — Index</p>
                        <p className="text-zinc-400">
                            Point the app at a folder. It scans every image and samples video frames
                            at ~1 FPS to build a list of visual moments.
                        </p>
                    </div>
                    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-4">
                        <p className="text-violet-400 font-semibold mb-1">Step 2 — Embed</p>
                        <p className="text-zinc-400">
                            Each frame or image is passed through CLIP, an AI model that converts
                            visuals into a numerical vector capturing its meaning and content.
                        </p>
                    </div>
                    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-4">
                        <p className="text-violet-400 font-semibold mb-1">Step 3 — Search</p>
                        <p className="text-zinc-400">
                            Your text query is also embedded with CLIP, then FAISS finds the closest
                            matching vectors — returning the most semantically relevant results instantly.
                            The percentage on each hit is cosine similarity × 100 (roughly −100% to +100%).
                            Text and image embeddings are aligned but not identical, so even very accurate
                            hits usually sit around <span className="text-zinc-300">20–45%</span>, not 99%:
                            nothing is wrong — CLIP rarely produces near-1.0 text–image cosine scores.
                        </p>
                    </div>
                </div>
            </section>

            <section>
                <h2 className="text-2xl font-semibold text-white mb-3">Demo</h2>
                <div className="rounded-xl border border-zinc-700 overflow-hidden max-h-[600px]">
                    <img
                        src="/demo.png"
                        alt="Screenshot of the app showing search results"
                        className="w-full object-cover object-top"
                    />
                </div>
            </section>

            <section>
                <h2 className="text-2xl font-semibold text-white mb-3">Tech stack</h2>
                <ul className="list-disc list-inside space-y-1 text-zinc-400 text-sm">
                    <li><span className="text-zinc-200">CLIP</span> — OpenAI's vision-language model for generating embeddings</li>
                    <li><span className="text-zinc-200">FAISS</span> — Facebook's library for fast similarity search over vectors</li>
                    <li><span className="text-zinc-200">FastAPI</span> — Python backend handling indexing and search requests</li>
                    <li><span className="text-zinc-200">React + Vite</span> — frontend UI</li>
                    <li><span className="text-zinc-200">OpenCV</span> — video frame extraction at ~1 FPS</li>
                </ul>
            </section>

            {/* Team */}
            <section>
                <h2 className="text-2xl font-semibold text-white mb-3">Team</h2>
                <p className="text-zinc-400 text-sm">
                    Built for CS 372 — Introduction to Applied Machine Learning, Duke University, Spring 2026.
                    <br />
                    Kabir Gupta & Michael Setji
                </p>
            </section>

        </main>
    )
}