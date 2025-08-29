# Changelog

## [0.8.1](https://github.com/Monadical-SAS/reflector/compare/v0.8.0...v0.8.1) (2025-08-29)


### Bug Fixes

* make webhook secret/url allowing null ([#590](https://github.com/Monadical-SAS/reflector/issues/590)) ([84a3812](https://github.com/Monadical-SAS/reflector/commit/84a381220bc606231d08d6f71d4babc818fa3c75))

## [0.8.0](https://github.com/Monadical-SAS/reflector/compare/v0.7.3...v0.8.0) (2025-08-29)


### Features

* **cleanup:** add automatic data retention for public instances ([#574](https://github.com/Monadical-SAS/reflector/issues/574)) ([6f0c7c1](https://github.com/Monadical-SAS/reflector/commit/6f0c7c1a5e751713366886c8e764c2009e12ba72))
* **rooms:** add webhook for transcript completion ([#578](https://github.com/Monadical-SAS/reflector/issues/578)) ([88ed7cf](https://github.com/Monadical-SAS/reflector/commit/88ed7cfa7804794b9b54cad4c3facc8a98cf85fd))


### Bug Fixes

* file pipeline status reporting and websocket updates ([#589](https://github.com/Monadical-SAS/reflector/issues/589)) ([9dfd769](https://github.com/Monadical-SAS/reflector/commit/9dfd76996f851cc52be54feea078adbc0816dc57))
* Igor/evaluation ([#575](https://github.com/Monadical-SAS/reflector/issues/575)) ([124ce03](https://github.com/Monadical-SAS/reflector/commit/124ce03bf86044c18313d27228a25da4bc20c9c5))
* optimize parakeet transcription batching algorithm ([#577](https://github.com/Monadical-SAS/reflector/issues/577)) ([7030e0f](https://github.com/Monadical-SAS/reflector/commit/7030e0f23649a8cf6c1eb6d5889684a41ce849ec))

## [0.7.3](https://github.com/Monadical-SAS/reflector/compare/v0.7.2...v0.7.3) (2025-08-22)


### Bug Fixes

* cleaned repo, and get git-leaks clean ([359280d](https://github.com/Monadical-SAS/reflector/commit/359280dd340433ba4402ed69034094884c825e67))
* restore previous behavior on live pipeline + audio downscaler ([#561](https://github.com/Monadical-SAS/reflector/issues/561)) ([9265d20](https://github.com/Monadical-SAS/reflector/commit/9265d201b590d23c628c5f19251b70f473859043))

## [0.7.2](https://github.com/Monadical-SAS/reflector/compare/v0.7.1...v0.7.2) (2025-08-21)


### Bug Fixes

* docker image not loading libgomp.so.1 for torch ([#560](https://github.com/Monadical-SAS/reflector/issues/560)) ([773fccd](https://github.com/Monadical-SAS/reflector/commit/773fccd93e887c3493abc2e4a4864dddce610177))
* include shared rooms to search ([#558](https://github.com/Monadical-SAS/reflector/issues/558)) ([499eced](https://github.com/Monadical-SAS/reflector/commit/499eced3360b84fb3a90e1c8a3b554290d21adc2))

## [0.7.1](https://github.com/Monadical-SAS/reflector/compare/v0.7.0...v0.7.1) (2025-08-21)


### Bug Fixes

* webvtt db null expectation mismatch ([#556](https://github.com/Monadical-SAS/reflector/issues/556)) ([e67ad1a](https://github.com/Monadical-SAS/reflector/commit/e67ad1a4a2054467bfeb1e0258fbac5868aaaf21))

## [0.7.0](https://github.com/Monadical-SAS/reflector/compare/v0.6.1...v0.7.0) (2025-08-21)


### Features

* delete recording with transcript ([#547](https://github.com/Monadical-SAS/reflector/issues/547)) ([99cc984](https://github.com/Monadical-SAS/reflector/commit/99cc9840b3f5de01e0adfbfae93234042d706d13))
* pipeline improvement with file processing, parakeet, silero-vad ([#540](https://github.com/Monadical-SAS/reflector/issues/540)) ([bcc29c9](https://github.com/Monadical-SAS/reflector/commit/bcc29c9e0050ae215f89d460e9d645aaf6a5e486))
* postgresql migration and removal of sqlite in pytest ([#546](https://github.com/Monadical-SAS/reflector/issues/546)) ([cd1990f](https://github.com/Monadical-SAS/reflector/commit/cd1990f8f0fe1503ef5069512f33777a73a93d7f))
* search backend ([#537](https://github.com/Monadical-SAS/reflector/issues/537)) ([5f9b892](https://github.com/Monadical-SAS/reflector/commit/5f9b89260c9ef7f3c921319719467df22830453f))
* search frontend  ([#551](https://github.com/Monadical-SAS/reflector/issues/551)) ([3657242](https://github.com/Monadical-SAS/reflector/commit/365724271ca6e615e3425125a69ae2b46ce39285))


### Bug Fixes

* evaluation cli event wrap ([#536](https://github.com/Monadical-SAS/reflector/issues/536)) ([941c3db](https://github.com/Monadical-SAS/reflector/commit/941c3db0bdacc7b61fea412f3746cc5a7cb67836))
* use structlog not logging ([#550](https://github.com/Monadical-SAS/reflector/issues/550)) ([27e2f81](https://github.com/Monadical-SAS/reflector/commit/27e2f81fda5232e53edc729d3e99c5ef03adbfe9))

## [0.6.1](https://github.com/Monadical-SAS/reflector/compare/v0.6.0...v0.6.1) (2025-08-06)


### Bug Fixes

* delayed waveform loading ([#538](https://github.com/Monadical-SAS/reflector/issues/538)) ([ef64146](https://github.com/Monadical-SAS/reflector/commit/ef64146325d03f64dd9a1fe40234fb3e7e957ae2))

## [0.6.0](https://github.com/Monadical-SAS/reflector/compare/v0.5.0...v0.6.0) (2025-08-05)


### ⚠ BREAKING CHANGES

* Configuration keys have changed. Update your .env file:
    - TRANSCRIPT_MODAL_API_KEY → TRANSCRIPT_API_KEY
    - LLM_MODAL_API_KEY → (removed, use TRANSCRIPT_API_KEY)
    - Add DIARIZATION_API_KEY and TRANSLATE_API_KEY if using those services

### Features

* implement service-specific Modal API keys with auto processor pattern ([#528](https://github.com/Monadical-SAS/reflector/issues/528)) ([650befb](https://github.com/Monadical-SAS/reflector/commit/650befb291c47a1f49e94a01ab37d8fdfcd2b65d))
* use llamaindex everywhere ([#525](https://github.com/Monadical-SAS/reflector/issues/525)) ([3141d17](https://github.com/Monadical-SAS/reflector/commit/3141d172bc4d3b3d533370c8e6e351ea762169bf))


### Miscellaneous Chores

* **main:** release 0.6.0 ([ecdbf00](https://github.com/Monadical-SAS/reflector/commit/ecdbf003ea2476c3e95fd231adaeb852f2943df0))

## [0.5.0](https://github.com/Monadical-SAS/reflector/compare/v0.4.0...v0.5.0) (2025-07-31)


### Features

* new summary using phi-4 and llama-index ([#519](https://github.com/Monadical-SAS/reflector/issues/519)) ([1bf9ce0](https://github.com/Monadical-SAS/reflector/commit/1bf9ce07c12f87f89e68a1dbb3b2c96c5ee62466))


### Bug Fixes

* remove unused settings and utils files ([#522](https://github.com/Monadical-SAS/reflector/issues/522)) ([2af4790](https://github.com/Monadical-SAS/reflector/commit/2af4790e4be9e588f282fbc1bb171c88a03d6479))

## [0.4.0](https://github.com/Monadical-SAS/reflector/compare/v0.3.2...v0.4.0) (2025-07-25)


### Features

* Diarization cli ([#509](https://github.com/Monadical-SAS/reflector/issues/509)) ([ffc8003](https://github.com/Monadical-SAS/reflector/commit/ffc8003e6dad236930a27d0fe3e2f2adfb793890))


### Bug Fixes

* remove faulty import Meeting ([#512](https://github.com/Monadical-SAS/reflector/issues/512)) ([0e68c79](https://github.com/Monadical-SAS/reflector/commit/0e68c798434e1b481f9482cc3a4702ea00365df4))
* room concurrency (theoretically) ([#511](https://github.com/Monadical-SAS/reflector/issues/511)) ([7bb3676](https://github.com/Monadical-SAS/reflector/commit/7bb367653afeb2778cff697a0eb217abf0b81b84))

## [0.3.2](https://github.com/Monadical-SAS/reflector/compare/v0.3.1...v0.3.2) (2025-07-22)


### Bug Fixes

* match font size for the filter sidebar ([#507](https://github.com/Monadical-SAS/reflector/issues/507)) ([4b8ba5d](https://github.com/Monadical-SAS/reflector/commit/4b8ba5db1733557e27b098ad3d1cdecadf97ae52))
* whereby consent not displaying ([#505](https://github.com/Monadical-SAS/reflector/issues/505)) ([1120552](https://github.com/Monadical-SAS/reflector/commit/1120552c2c83d084d3a39272ad49b6aeda1af98f))

## [0.3.1](https://github.com/Monadical-SAS/reflector/compare/v0.3.0...v0.3.1) (2025-07-22)


### Bug Fixes

* remove fief out of the source code ([#502](https://github.com/Monadical-SAS/reflector/issues/502)) ([890dd15](https://github.com/Monadical-SAS/reflector/commit/890dd15ba5a2be10dbb841e9aeb75d377885f4af))
* remove primary color for room action menu ([#504](https://github.com/Monadical-SAS/reflector/issues/504)) ([2e33f89](https://github.com/Monadical-SAS/reflector/commit/2e33f89c0f9e5fbaafa80e8d2ae9788450ea2f31))

## [0.3.0](https://github.com/Monadical-SAS/reflector/compare/v0.2.1...v0.3.0) (2025-07-21)


### Features

* migrate from chakra 2 to chakra 3 ([#500](https://github.com/Monadical-SAS/reflector/issues/500)) ([a858464](https://github.com/Monadical-SAS/reflector/commit/a858464c7a80e5497acf801d933bf04092f8b526))

## [0.2.1](https://github.com/Monadical-SAS/reflector/compare/v0.2.0...v0.2.1) (2025-07-18)


### Bug Fixes

* separate browsing page into different components, limit to 10 by default ([#498](https://github.com/Monadical-SAS/reflector/issues/498)) ([c752da6](https://github.com/Monadical-SAS/reflector/commit/c752da6b97c96318aff079a5b2a6eceadfbfcad1))

## [0.2.0](https://github.com/Monadical-SAS/reflector/compare/0.1.1...v0.2.0) (2025-07-17)


### Features

* improve transcript listing with room_id ([#496](https://github.com/Monadical-SAS/reflector/issues/496)) ([d2b5de5](https://github.com/Monadical-SAS/reflector/commit/d2b5de543fc0617fc220caa6a8a290e4040cb10b))


### Bug Fixes

* don't attempt to load waveform/mp3 if audio was deleted ([#495](https://github.com/Monadical-SAS/reflector/issues/495)) ([f4578a7](https://github.com/Monadical-SAS/reflector/commit/f4578a743fd0f20312fbd242fa9cccdfaeb20a9e))

## [0.1.1](https://github.com/Monadical-SAS/reflector/compare/0.1.0...v0.1.1) (2025-07-17)


### Bug Fixes

* postgres database not connecting in worker ([#492](https://github.com/Monadical-SAS/reflector/issues/492)) ([123d09f](https://github.com/Monadical-SAS/reflector/commit/123d09fdacef7f5a84541cf01732d4f5b6b9d2d0))
* process meetings with utc ([#493](https://github.com/Monadical-SAS/reflector/issues/493)) ([f3c85e1](https://github.com/Monadical-SAS/reflector/commit/f3c85e1eb97cd893840125ed056dcb290fccb612))
* punkt -&gt; punkt_tab + pre-download nltk packages to prevent runtime not working ([#489](https://github.com/Monadical-SAS/reflector/issues/489)) ([c22487b](https://github.com/Monadical-SAS/reflector/commit/c22487b41f311a3fdba2eac04c7637bd396cccee))
* rename averaged_perceptron_tagger to averaged_perceptron_tagger_eng ([#491](https://github.com/Monadical-SAS/reflector/issues/491)) ([a7b7846](https://github.com/Monadical-SAS/reflector/commit/a7b78462419b3af81c6dbf1ddfccb3d532f660a3))
