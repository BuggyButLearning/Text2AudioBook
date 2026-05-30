import types

import pytest

from main import _format_discovery_status, _validate_conversion_inputs
from model_discovery import DiscoveryResult, Source


class TestValidateConversionInputs:
    def test_all_populated_returns_ok(self):
        ok, missing = _validate_conversion_inputs("file.txt", "out", "tts-1")
        assert ok is True
        assert missing == []

    def test_single_empty_returns_that_field(self):
        ok, missing = _validate_conversion_inputs("", "out", "tts-1")
        assert ok is False
        assert missing == ["Input File"]

    def test_all_empty_returns_all_fields(self):
        ok, missing = _validate_conversion_inputs("", "", "")
        assert ok is False
        assert missing == ["Input File", "Output File Name", "Model"]

    def test_whitespace_only_counts_as_empty(self):
        ok, missing = _validate_conversion_inputs("file.txt", "   ", "tts-1")
        assert ok is False
        assert "Output File Name" in missing

    def test_none_values_count_as_empty(self):
        ok, missing = _validate_conversion_inputs(None, "out", "tts-1")
        assert ok is False
        assert missing == ["Input File"]

    def test_field_order_is_stable(self):
        ok, missing = _validate_conversion_inputs("", "", "tts-1")
        assert missing == ["Input File", "Output File Name"]


class TestFormatDiscoveryStatus:
    def test_live_singular(self):
        r = DiscoveryResult("OpenAI", ("tts-1",), Source.LIVE, None)
        assert _format_discovery_status(r) == "Loaded 1 OpenAI model"

    def test_live_plural(self):
        r = DiscoveryResult("OpenAI", ("tts-1", "tts-1-hd"), Source.LIVE, None)
        assert _format_discovery_status(r) == "Loaded 2 OpenAI models"

    def test_empty_with_reason(self):
        r = DiscoveryResult("Ollama", (), Source.EMPTY, "no models matched allowlist")
        msg = _format_discovery_status(r)
        assert "No Ollama models available" in msg
        assert "no models matched allowlist" in msg

    def test_empty_without_reason(self):
        r = DiscoveryResult("Ollama", (), Source.EMPTY, None)
        assert _format_discovery_status(r) == "No Ollama models available"

    def test_fallback_with_reason(self):
        r = DiscoveryResult("OpenAI", ("tts-1",), Source.FALLBACK, "api down")
        msg = _format_discovery_status(r)
        assert "OpenAI discovery failed" in msg
        assert "api down" in msg
        assert "fallback list" in msg

    def test_fallback_without_reason_is_registry_list(self):
        # FALLBACK with no error means provider has no live-probe path (e.g. Kokoro
        # local-hf before Phase 6.2). Do NOT say "discovery failed" -- nothing failed.
        r = DiscoveryResult("Kokoro", ("kokoro-82m",), Source.FALLBACK, None)
        msg = _format_discovery_status(r)
        assert "discovery failed" not in msg
        assert "Kokoro" in msg
        assert "registry list" in msg
        assert "1 model" in msg

    def test_credential_scrubbed_reason_carries_through(self):
        r = DiscoveryResult(
            "OpenAI", ("tts-1",), Source.FALLBACK,
            "Auth failed for ***REDACTED*** at https://api.openai.com/v1/models",
        )
        msg = _format_discovery_status(r)
        assert "***REDACTED***" in msg
        assert "sk-" not in msg


class TestRunConversionWorker:
    """Audit S2: programmatic smoke test for the worker function.
    Catches a regression where someone bypasses the _thread_safe_status chokepoint
    by calling status_var.set() directly from the worker thread. Uses a fake root
    with a synchronous .after() so the test runs without a real GUI."""

    def _setup(self, monkeypatch, tmp_path):
        import main

        captured = {"status_calls": [], "after_calls": []}

        class FakeRoot:
            def after(self_inner, delay, callback):
                captured["after_calls"].append(delay)
                callback()

        class FakeStatusVar:
            def set(self_inner, value):
                captured["status_calls"].append(value)

        # raising=False because root, status_var, set_controls_enabled, save_user_defaults
        # are only created inside create_app() at GUI startup; they don't exist at module-import
        # time. monkeypatch needs to ADD them, not REPLACE.
        monkeypatch.setattr(main, "root", FakeRoot(), raising=False)
        monkeypatch.setattr(main, "status_var", FakeStatusVar(), raising=False)
        monkeypatch.setattr(
            main, "set_controls_enabled",
            lambda enabled: captured.setdefault("set_controls_enabled_calls", []).append(enabled),
            raising=False,
        )
        monkeypatch.setattr(
            main, "save_user_defaults",
            lambda *_a, **_kw: captured.setdefault("save_user_defaults_calls", []).append(True),
            raising=False,
        )

        monkeypatch.setattr(main, "messagebox", types.SimpleNamespace(
            showinfo=lambda *a, **kw: captured.setdefault("showinfo_calls", []).append(a),
            showerror=lambda *a, **kw: captured.setdefault("showerror_calls", []).append(a),
            showwarning=lambda *a, **kw: captured.setdefault("showwarning_calls", []).append(a),
        ))

        monkeypatch.setattr(main, "read_text_from_file", lambda path: "Hello world.")
        monkeypatch.setattr(
            main, "split_text",
            lambda text: (["Hello world."], [0], ["Hello world."]),
        )
        fake_output_chunk = tmp_path / "chunk_part_1_xyz.mp3"
        monkeypatch.setattr(
            main, "convert_text_to_speech",
            lambda chunks, settings, folder, ts, status_callback=None: (
                [status_callback("chunk 1 attempt 1/3 ...") if status_callback else None]
                and [fake_output_chunk]
            ),
        )
        monkeypatch.setattr(main, "concatenate_audio_files", lambda files, out: None)

        return main, captured

    def test_worker_status_sequence_on_success(self, monkeypatch, tmp_path):
        main, captured = self._setup(monkeypatch, tmp_path)

        settings = types.SimpleNamespace(
            provider="OpenAI", model="tts-1", voice="alloy",
            speed=1.0, response_format="mp3", openai_api_key="sk-x",
            max_concurrency=1,
        )
        main._run_conversion_worker(
            input_file="ignored.txt",
            output_folder_path=tmp_path,
            output_filename="audiobook",
            settings=settings,
            timestamp="20260521_120000",
        )

        joined = " | ".join(captured["status_calls"])
        assert "Reading input" in joined
        assert "Preparing text" in joined
        assert "Converting 1 chunk" in joined
        assert "Merging audio" in joined
        assert "Conversion completed" in joined
        assert len(captured["after_calls"]) >= len(captured["status_calls"])

    def test_worker_resets_state_in_finally(self, monkeypatch, tmp_path):
        main, captured = self._setup(monkeypatch, tmp_path)
        main._conversion_in_progress = True

        settings = types.SimpleNamespace(
            provider="OpenAI", model="tts-1", voice="alloy",
            speed=1.0, response_format="mp3", openai_api_key="sk-x",
            max_concurrency=1,
        )
        main._run_conversion_worker(
            input_file="ignored.txt",
            output_folder_path=tmp_path,
            output_filename="audiobook",
            settings=settings,
            timestamp="20260521_120000",
        )
        assert main._conversion_in_progress is False
        assert True in captured.get("set_controls_enabled_calls", [])

    def test_worker_handles_read_failure_gracefully(self, monkeypatch, tmp_path):
        main, captured = self._setup(monkeypatch, tmp_path)
        monkeypatch.setattr(main, "read_text_from_file", lambda path: None)
        main._conversion_in_progress = True

        settings = types.SimpleNamespace(
            provider="OpenAI", model="tts-1", voice="alloy",
            speed=1.0, response_format="mp3", openai_api_key="sk-x",
            max_concurrency=1,
        )
        main._run_conversion_worker(
            input_file="ignored.txt",
            output_folder_path=tmp_path,
            output_filename="audiobook",
            settings=settings,
            timestamp="20260521_120000",
        )
        assert main._conversion_in_progress is False
        assert "Failed to read input" in " | ".join(captured["status_calls"])

    def test_worker_handles_synthesis_failure_gracefully(self, monkeypatch, tmp_path):
        main, captured = self._setup(monkeypatch, tmp_path)
        monkeypatch.setattr(main, "convert_text_to_speech", lambda *_a, **_kw: [])
        main._conversion_in_progress = True

        settings = types.SimpleNamespace(
            provider="OpenAI", model="tts-1", voice="alloy",
            speed=1.0, response_format="mp3", openai_api_key="sk-x",
            max_concurrency=1,
        )
        main._run_conversion_worker(
            input_file="ignored.txt",
            output_folder_path=tmp_path,
            output_filename="audiobook",
            settings=settings,
            timestamp="20260521_120000",
        )
        assert main._conversion_in_progress is False
        assert "Conversion failed" in " | ".join(captured["status_calls"])
        assert len(captured.get("showerror_calls", [])) >= 1


class TestRefreshModelsBehavior:
    """Programmatic coverage for refresh_models. Verifies the audit-mandated
    invalidate-then-discover sequence and the DiscoveryResult routing into the
    status label / model dropdown / warning dialog. Does not require a real Tk root."""

    def _setup(self, monkeypatch):
        import main

        captured = {
            "invalidate_calls": [],
            "discover_calls": [],
            "status_messages": [],
            "model_var_set_values": [],
            "model_menu_values": [],
            "showwarning_calls": [],
            "call_order": [],
        }

        class FakeStringVar:
            def __init__(self_inner, value=""):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

            def set(self_inner, value):
                self_inner._value = value
                captured["model_var_set_values"].append(value)

        class FakeProviderVar:
            def __init__(self_inner, value="OpenAI"):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

        class FakeStatusVar:
            def set(self_inner, value):
                captured["status_messages"].append(value)

        class FakeModelMenu:
            def configure(self_inner, **kwargs):
                if "values" in kwargs:
                    captured["model_menu_values"].append(list(kwargs["values"]))

        class FakeRoot:
            def update_idletasks(self_inner):
                pass

        monkeypatch.setattr(main, "root", FakeRoot(), raising=False)
        monkeypatch.setattr(main, "status_var", FakeStatusVar(), raising=False)
        monkeypatch.setattr(main, "model_var", FakeStringVar("tts-1"), raising=False)
        monkeypatch.setattr(main, "model_menu", FakeModelMenu(), raising=False)
        monkeypatch.setattr(main, "provider_var", FakeProviderVar("OpenAI"), raising=False)

        def fake_invalidate(provider):
            captured["invalidate_calls"].append(provider)
            captured["call_order"].append(("invalidate", provider))

        monkeypatch.setattr(main, "invalidate_cache", fake_invalidate)

        monkeypatch.setattr(main, "messagebox", types.SimpleNamespace(
            showwarning=lambda *a, **kw: captured["showwarning_calls"].append(a),
            showerror=lambda *a, **kw: None,
            showinfo=lambda *a, **kw: None,
        ))

        monkeypatch.setattr(
            main, "build_runtime_settings",
            lambda **kw: types.SimpleNamespace(
                openai_api_key="sk-test",
                ollama_base_url="http://localhost:11434",
            ),
        )

        return main, captured

    def test_refresh_calls_invalidate_before_discover(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        from model_discovery import DiscoveryResult, Source

        def fake_discover(provider, **kwargs):
            captured["discover_calls"].append((provider, kwargs))
            captured["call_order"].append(("discover", provider))
            return DiscoveryResult("OpenAI", ("tts-1", "tts-1-hd"), Source.LIVE, None)

        monkeypatch.setattr(main, "discover_models", fake_discover)

        main.refresh_models()

        # Sequence MUST be invalidate -> discover
        assert captured["call_order"][0] == ("invalidate", "OpenAI")
        assert captured["call_order"][1] == ("discover", "OpenAI")
        assert captured["invalidate_calls"] == ["OpenAI"]

    def test_refresh_use_cache_false(self, monkeypatch):
        """Audit AC-2: discover_models MUST be called with use_cache=False so the
        button is truthful even if invalidate_cache had a bug."""
        main, captured = self._setup(monkeypatch)
        from model_discovery import DiscoveryResult, Source

        def fake_discover(provider, **kwargs):
            captured["discover_calls"].append((provider, kwargs))
            return DiscoveryResult("OpenAI", ("tts-1",), Source.LIVE, None)

        monkeypatch.setattr(main, "discover_models", fake_discover)
        main.refresh_models()
        _, kwargs = captured["discover_calls"][0]
        assert kwargs.get("use_cache") is False

    def test_refresh_populates_dropdown_on_live(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        from model_discovery import DiscoveryResult, Source

        monkeypatch.setattr(
            main, "discover_models",
            lambda *a, **kw: DiscoveryResult("OpenAI", ("tts-1", "tts-1-hd"), Source.LIVE, None),
        )
        main.refresh_models()
        assert captured["model_menu_values"][-1] == ["tts-1", "tts-1-hd"]
        assert captured["model_var_set_values"][-1] == "tts-1"
        assert any("Loaded 2 OpenAI models" in m for m in captured["status_messages"])

    def test_refresh_empty_with_reason_status(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        main.provider_var._value = "Ollama"
        from model_discovery import DiscoveryResult, Source

        monkeypatch.setattr(
            main, "discover_models",
            lambda *a, **kw: DiscoveryResult("Ollama", (), Source.EMPTY, "no models matched allowlist"),
        )
        main.refresh_models()
        joined = " | ".join(captured["status_messages"])
        assert "No Ollama models available" in joined
        assert "no models matched allowlist" in joined
        # Audit AC-2: Ollama-specific warning dialog on EMPTY source
        assert len(captured["showwarning_calls"]) == 1

    def test_refresh_fallback_status(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        from model_discovery import DiscoveryResult, Source

        monkeypatch.setattr(
            main, "discover_models",
            lambda *a, **kw: DiscoveryResult("OpenAI", ("tts-1",), Source.FALLBACK, "Auth failed for ***REDACTED***"),
        )
        main.refresh_models()
        joined = " | ".join(captured["status_messages"])
        assert "OpenAI discovery failed" in joined
        assert "***REDACTED***" in joined
        assert "sk-" not in joined


class TestSetControlsEnabled:
    """Audit AC-4: set_controls_enabled MUST toggle dropdowns (provider/quality/
    model/voice) in addition to the 4 buttons. Uses fake widgets capturing
    .config(state=...) calls -- no real Tk root needed."""

    def _setup(self, monkeypatch):
        import main

        states = {}

        class FakeWidget:
            def __init__(self_inner, name):
                self_inner._name = name
                states[name] = None

            def config(self_inner, state=None, **_kw):
                if state is not None:
                    states[self_inner._name] = state

        class FakeProviderVar:
            def __init__(self_inner, value="OpenAI"):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

        for name in ["browse_file_button", "browse_output_button",
                     "refresh_models_button", "start_button",
                     "provider_menu", "quality_menu", "model_menu", "voice_menu"]:
            monkeypatch.setattr(main, name, FakeWidget(name), raising=False)
        monkeypatch.setattr(main, "provider_var", FakeProviderVar("OpenAI"), raising=False)

        return main, states

    def test_disable_locks_buttons_and_dropdowns(self, monkeypatch):
        main, states = self._setup(monkeypatch)
        main.set_controls_enabled(False)
        # All buttons + dropdowns must be in a disabled-ish state
        for name in ["browse_file_button", "browse_output_button",
                     "refresh_models_button", "start_button"]:
            assert states[name] == "disabled", f"{name} not disabled (got {states[name]!r})"
        for name in ["provider_menu", "quality_menu", "model_menu", "voice_menu"]:
            assert states[name] == "disabled", f"{name} not disabled (got {states[name]!r})"

    def test_enable_restores_buttons_and_readonly_dropdowns(self, monkeypatch):
        main, states = self._setup(monkeypatch)
        main.set_controls_enabled(True)
        for name in ["browse_file_button", "browse_output_button",
                     "refresh_models_button", "start_button"]:
            assert states[name] == "normal", f"{name} not normal (got {states[name]!r})"
        for name in ["provider_menu", "quality_menu", "model_menu"]:
            assert states[name] == "readonly", f"{name} not readonly (got {states[name]!r})"
        # voice_menu is readonly for OpenAI, disabled for Ollama
        assert states["voice_menu"] == "readonly"

    def test_enable_voice_disabled_when_ollama(self, monkeypatch):
        main, states = self._setup(monkeypatch)
        main.provider_var._value = "Ollama"
        main.set_controls_enabled(True)
        assert states["voice_menu"] == "disabled", (
            f"voice_menu should be disabled when provider=Ollama; got {states['voice_menu']!r}"
        )


class TestStartConversionGuards:
    """Validation rejection + concurrent-conversion guard. Does not spawn real threads."""

    def _setup(self, monkeypatch):
        import main

        captured = {
            "showerror_calls": [],
            "thread_starts": 0,
            "set_controls_calls": [],
        }

        class FakeEntry:
            def __init__(self_inner, value=""):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

        class FakeStringVar:
            def __init__(self_inner, value=""):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

        monkeypatch.setattr(main, "file_entry", FakeEntry(""), raising=False)
        monkeypatch.setattr(main, "folder_entry", FakeEntry("/tmp"), raising=False)
        monkeypatch.setattr(main, "output_name_entry", FakeEntry(""), raising=False)
        monkeypatch.setattr(main, "provider_var", FakeStringVar("OpenAI"), raising=False)
        monkeypatch.setattr(main, "quality_var", FakeStringVar("Balanced"), raising=False)
        monkeypatch.setattr(main, "model_var", FakeStringVar(""), raising=False)
        monkeypatch.setattr(main, "voice_var", FakeStringVar("alloy"), raising=False)
        monkeypatch.setattr(
            main, "set_controls_enabled",
            lambda enabled: captured["set_controls_calls"].append(enabled),
            raising=False,
        )
        monkeypatch.setattr(main, "messagebox", types.SimpleNamespace(
            showerror=lambda *a, **kw: captured["showerror_calls"].append(a),
            showinfo=lambda *a, **kw: None,
            showwarning=lambda *a, **kw: None,
        ))

        class FakeThread:
            def __init__(self_inner, *_a, **_kw):
                captured["thread_starts"] += 1

            def start(self_inner):
                pass

        monkeypatch.setattr(main.threading, "Thread", FakeThread)

        # Reset guard between tests
        main._conversion_in_progress = False

        return main, captured

    def test_empty_inputs_rejected_with_enumerated_message(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        # All fields empty
        main.start_conversion()
        assert captured["thread_starts"] == 0, "thread should NOT spawn when validation fails"
        assert len(captured["showerror_calls"]) == 1
        msg = captured["showerror_calls"][0][1]
        assert "Input File" in msg
        assert "Output File Name" in msg
        assert "Model" in msg

    def test_concurrent_click_does_not_spawn_second_worker(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        # Populate all required fields
        main.file_entry._value = "input.txt"
        main.output_name_entry._value = "out"
        main.model_var._value = "tts-1"
        # First click sets the guard
        main._conversion_in_progress = True
        main.start_conversion()
        # No new thread spawned because guard is set
        assert captured["thread_starts"] == 0
        # No error dialog -- silent rejection per audit S1 spec
        assert captured["showerror_calls"] == []


class TestAutosizeWindow:
    """_autosize_window computes geometry from widget reqsize + padding,
    floored at (min_w, min_h). No real Tk root needed."""

    def _fake_window(self, req_w, req_h):
        captured = {"geometry": None, "minsize": None, "idletasks_calls": 0}

        class FakeWindow:
            def update_idletasks(self_inner):
                captured["idletasks_calls"] += 1
            def winfo_reqwidth(self_inner):
                return req_w
            def winfo_reqheight(self_inner):
                return req_h
            def geometry(self_inner, spec):
                captured["geometry"] = spec
            def minsize(self_inner, w, h):
                captured["minsize"] = (w, h)
        return FakeWindow(), captured

    def test_uses_reqsize_plus_padding_when_above_floor(self):
        import main
        window, captured = self._fake_window(800, 500)
        main._autosize_window(window, padding_w=24, padding_h=24, min_w=720, min_h=390)
        assert captured["geometry"] == "824x524"
        assert captured["minsize"] == (824, 524)
        assert captured["idletasks_calls"] == 1

    def test_floors_to_min_when_reqsize_too_small(self):
        import main
        window, captured = self._fake_window(400, 300)
        main._autosize_window(window, padding_w=24, padding_h=24, min_w=720, min_h=390)
        # 400+24=424 < 720 floor; 300+24=324 < 390 floor
        assert captured["geometry"] == "720x390"
        assert captured["minsize"] == (720, 390)

    def test_partial_floor_mixed(self):
        import main
        window, captured = self._fake_window(900, 300)
        main._autosize_window(window, padding_w=24, padding_h=24, min_w=720, min_h=390)
        # Width above floor: 900+24=924; height below: 300+24=324 -> 390
        assert captured["geometry"] == "924x390"

    def test_calls_update_idletasks_before_measuring(self):
        """Tk reqsize is only valid after pending geometry mgmt has run."""
        import main
        window, captured = self._fake_window(800, 500)
        main._autosize_window(window)
        assert captured["idletasks_calls"] == 1


class TestOnProviderChange:
    """on_provider_change refreshes models and toggles voice_menu state."""

    def _setup(self, monkeypatch):
        import main

        captured = {"refresh_called": 0, "voice_menu_state": None}

        class FakeStringVar:
            def __init__(self_inner, value):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

            def set(self_inner, value):
                self_inner._value = value

        class FakeVoiceMenu:
            def config(self_inner, state=None, **_kw):
                if state is not None:
                    captured["voice_menu_state"] = state

            def configure(self_inner, values=None, **_kw):
                if values is not None:
                    captured.setdefault("voice_menu_values", []).append(list(values))

        monkeypatch.setattr(main, "provider_var", FakeStringVar("OpenAI"), raising=False)
        monkeypatch.setattr(main, "voice_var", FakeStringVar("alloy"), raising=False)
        monkeypatch.setattr(main, "voice_menu", FakeVoiceMenu(), raising=False)
        monkeypatch.setattr(
            main, "refresh_models",
            lambda: captured.update(refresh_called=captured["refresh_called"] + 1),
            raising=False,
        )

        return main, captured

    def test_ollama_disables_voice_menu(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        main.provider_var._value = "Ollama"
        main.on_provider_change()
        assert captured["voice_menu_state"] == "disabled"
        assert captured["refresh_called"] == 1

    def test_openai_makes_voice_readonly(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        main.provider_var._value = "OpenAI"
        main.on_provider_change()
        assert captured["voice_menu_state"] == "readonly"
        assert captured["refresh_called"] == 1

    def test_kokoro_populates_voice_list_from_registry(self, monkeypatch):
        """Capability-driven: switching to Kokoro must repopulate voice_menu with
        the registry's Kokoro voices, not leave it stuck on OPENAI_VOICES."""
        main, captured = self._setup(monkeypatch)
        main.provider_var._value = "Kokoro"
        main.on_provider_change()
        assert captured["voice_menu_state"] == "readonly"
        last_values = captured["voice_menu_values"][-1]
        # Registry ships 20 American-English Kokoro voices for v0.1.
        assert "af_heart" in last_values
        assert "am_michael" in last_values
        # voice_var should reset to the first valid Kokoro voice (was "alloy",
        # which is not in Kokoro voices).
        assert main.voice_var.get() in last_values


class TestRegistryDrivenProviderOptions:
    """Drift guard: the provider dropdown must reflect providers.PROVIDER_REGISTRY,
    not a hardcoded list. Caught a real bug where 'Kokoro' was registered but never
    surfaced in the GUI."""

    def test_provider_options_includes_all_registry_providers(self):
        import main
        from providers import list_providers
        registry_names = set(list_providers())
        assert set(main.provider_options) == registry_names, (
            f"provider_options drift: registry={registry_names} dropdown={main.provider_options}"
        )

    def test_provider_options_includes_kokoro(self):
        import main
        assert "Kokoro" in main.provider_options


class TestKokoroSynthesisGuard:
    """Phase 6.2 not yet landed: clicking Start with provider=Kokoro must reject
    with a clear error, NOT silently route the Kokoro model name to OpenAI."""

    def _setup(self, monkeypatch):
        import main

        captured = {"showerror_calls": [], "thread_starts": 0}

        class FakeEntry:
            def __init__(self_inner, value=""):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

        class FakeStringVar:
            def __init__(self_inner, value=""):
                self_inner._value = value

            def get(self_inner):
                return self_inner._value

        monkeypatch.setattr(main, "file_entry", FakeEntry("input.txt"), raising=False)
        monkeypatch.setattr(main, "folder_entry", FakeEntry("/tmp"), raising=False)
        monkeypatch.setattr(main, "output_name_entry", FakeEntry("audiobook"), raising=False)
        monkeypatch.setattr(main, "provider_var", FakeStringVar("Kokoro"), raising=False)
        monkeypatch.setattr(main, "quality_var", FakeStringVar("Balanced"), raising=False)
        monkeypatch.setattr(main, "model_var", FakeStringVar("kokoro-82m"), raising=False)
        monkeypatch.setattr(main, "voice_var", FakeStringVar("af_heart"), raising=False)
        monkeypatch.setattr(
            main, "set_controls_enabled",
            lambda enabled: None,
            raising=False,
        )
        monkeypatch.setattr(main, "messagebox", types.SimpleNamespace(
            showerror=lambda *a, **kw: captured["showerror_calls"].append(a),
            showinfo=lambda *a, **kw: None,
            showwarning=lambda *a, **kw: None,
        ))

        class FakeThread:
            def __init__(self_inner, *_a, **_kw):
                captured["thread_starts"] += 1

            def start(self_inner):
                pass

        monkeypatch.setattr(main.threading, "Thread", FakeThread)
        main._conversion_in_progress = False
        return main, captured

    def test_kokoro_start_offers_install_when_kokoro_lib_missing(self, monkeypatch):
        """Phase 6.2.1: kokoro lib missing + espeak OK → askyesno install prompt;
        on 'yes', a background installer thread is spawned (NOT a conversion worker)."""
        main, captured = self._setup(monkeypatch)
        captured["askyesno_calls"] = []
        captured["install_thread_spawned"] = False

        import kokoro_synthesis
        monkeypatch.setattr(kokoro_synthesis, "kokoro_ready", lambda: (False, "kokoro missing"))
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available", lambda: (False, "kokoro missing"))
        monkeypatch.setattr(kokoro_synthesis, "espeak_ng_available", lambda: (True, None))

        # askyesno -> True (user accepts install)
        main.messagebox.askyesno = lambda *a, **kw: captured["askyesno_calls"].append(a) or True

        # Override FakeThread to distinguish installer vs conversion worker.
        class FakeInstallerThread:
            def __init__(self_inner, target, args, daemon):
                captured["install_thread_spawned"] = True
                captured["install_target"] = target
                captured["install_args"] = args
            def start(self_inner): pass
        monkeypatch.setattr(main.threading, "Thread", FakeInstallerThread)

        main.start_conversion()
        assert len(captured["askyesno_calls"]) == 1, "user must be prompted before install"
        assert captured["install_thread_spawned"] is True
        # The installer should be the _run_kokoro_installer function, not _run_conversion_worker.
        assert captured["install_target"].__name__ == "_run_kokoro_installer"
        # No showerror — user got the install prompt instead.
        assert captured["showerror_calls"] == []

    def test_kokoro_start_aborts_when_user_declines_install(self, monkeypatch):
        main, captured = self._setup(monkeypatch)
        captured["thread_spawned"] = False

        import kokoro_synthesis
        monkeypatch.setattr(kokoro_synthesis, "kokoro_ready", lambda: (False, "kokoro missing"))
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available", lambda: (False, "kokoro missing"))
        monkeypatch.setattr(kokoro_synthesis, "espeak_ng_available", lambda: (True, None))
        main.messagebox.askyesno = lambda *a, **kw: False  # user clicks No

        class FailIfSpawned:
            def __init__(self_inner, *_a, **_kw): captured["thread_spawned"] = True
            def start(self_inner): pass
        monkeypatch.setattr(main.threading, "Thread", FailIfSpawned)

        main.start_conversion()
        assert captured["thread_spawned"] is False, "must NOT spawn installer when user declines"

    def test_kokoro_start_proceeds_when_lib_present(self, monkeypatch):
        """kokoro_available True is the ONLY hard gate now (espeak softened)."""
        main, captured = self._setup(monkeypatch)
        import kokoro_synthesis
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available", lambda: (True, None))
        monkeypatch.setattr(
            main, "build_runtime_settings",
            lambda **kw: types.SimpleNamespace(
                openai_api_key="sk-x",
                ollama_base_url="http://localhost:11434",
            ),
        )
        main.start_conversion()
        assert captured["thread_starts"] == 1
        assert captured["showerror_calls"] == []
