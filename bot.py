#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat Quickstart Example — ElevenLabs + Daily.

Ejecuta un bot de voz que puedes abrir desde /client (o te redirige a Daily).
Forzamos un saludo al conectar para validar audio de salida.

Requiere:
- Deepgram (STT)    -> DEEPGRAM_API_KEY
- OpenAI (LLM)      -> OPENAI_API_KEY
- ElevenLabs (TTS)  -> ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (opcional)
- Daily (transporte)-> DAILY_API_KEY (si usas --transport daily)
"""

import os
from dotenv import load_dotenv
from loguru import logger

from pipecat.frames.frames import LLMRunFrame
from pipecat.audio.vad.silero import SileroVADAnalyzer

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor

from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService

from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams


print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds first run only)\n")

logger.info("Loading Silero VAD model...")
load_dotenv(override=True)  # carga .env si existe

# ---------------------------------------------------------------------
# Componentes principales (STT, TTS, LLM)
# ---------------------------------------------------------------------

def build_services():
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),        
        voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
        sample_rate=48000,       
    )

    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))
    return stt, tts, llm


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting bot")

    stt, tts, llm = build_services()

    messages = [
        {
            "role": "system",
            "content": "You are a friendly AI assistant. Respond naturally and keep your answers conversational.",
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),              # Entrada del usuario (transporte)
            rtvi,                           # Procesador RTVI
            stt,                            # STT
            context_aggregator.user(),      # Agrega usuario al contexto
            llm,                            # LLM
            tts,                            # TTS
            transport.output(),             # Salida del bot (transporte)
            context_aggregator.assistant(), # Agrega respuesta del asistente al contexto
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    # ------------------------------
    # HANDLERS DE TRANSPORTE (nuevo)
    # ------------------------------
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        # Fuerza un saludo inmediato (útil para validar audio)
        messages.append(
            {
                "role": "system",
                "content": "Say hello and briefly introduce yourself.",
            }
        )
        await task.queue_frames([LLMRunFrame()])
        logger.info("Queued LLMRunFrame for greeting")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Punto de entrada del bot para el runner."""

    transport_params = {
        # Daily (recomendado en PaaS)
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            output_sample_rate=48000,
        ),
        # WebRTC embebido (puede requerir TURN en PaaS)
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
