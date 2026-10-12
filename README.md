# Forecast in a Pocket - benchmarks

**Forecast in a Pocket** runs ECMWF's real **AIFS 2.0** global weather models (253 M parameters, 0.25° grid, 542,080
points, trained with the Anemoi framework) on an Android phone's Hexagon NPU: a 10-day forecast in about 25 minutes
on a Snapdragon 8 Gen 2. This repository collects the runs people's phones have computed and keeps the leaderboard.

## Submit a run

From the app: when a forecast completes, the notification offers **Send benchmark**, and the About screen (tap the
FBK logo) has the same button for the last completed run. It opens a prefilled issue form here in your browser.
Check it, press *Submit*. Nothing leaves the phone before that, and a GitHub account is all it needs.

A crash is reported the same way (About → *Report the crash*); please attach the full log from *Share log* if you can.

## How a run is verified

The app computes the SHA-256 of one output column of the first step (2 m temperature, 542,080 fp16 values). A phone's
outputs are bit-reproducible for a given Hexagon generation, so a run of the **shipped case** (the same ECMWF analysis
every phone computes) whose hash equals the known hash of its chip was really produced by the model on that chip.
The known hashes are in [`data/known_hashes.json`](data/known_hashes.json); a chip we have no hash for is listed as
*new chip* until a second, independent phone reports the same hash. Runs from the latest ECMWF analysis are listed as
*unverified* (their hash cannot be checked against anything).

The Action in [`.github/workflows/leaderboard.yml`](.github/workflows/leaderboard.yml) parses every benchmark issue,
stores it in [`data/benchmarks.json`](data/benchmarks.json), rewrites the table below and comments its verdict on the
issue. Edit the issue to correct a field; it runs again.

## Leaderboard

Seconds per 6-hour step, fastest first. One step = the whole model: encoder, 16 transformer layers, decoder, on the NPU.

<!-- leaderboard:start -->

### AIFS-single

| # | device | SoC | s/step | steps | total min | NPU max | initial conditions | app | status | by |
|--:|---|---|--:|--:|--:|--:|---|---|---|---|
| 1 | motorola motorola edge 40 pro | sm8550 | 36.5 | 12 | 4 | 74 °C | Shipped case | 0.2-1614bd0 | ✓ verified | [@franchg](https://github.com/DSIP-FBK/forecast-in-a-pocket-benchmarks/issues/1) |

### AIFS-ENS (one member)

_no submissions yet_

<!-- leaderboard:end -->

## Reference

| chip | HTP | phone | AIFS-single | AIFS-ENS |
|---|---|---|--:|--:|
| SM8550 (Snapdragon 8 Gen 2) | v73 | Motorola Edge 40 Pro | 32.6 s/step, 10 days in 24.8 min | 56.5 s/step, 40.6 min |
| SM8750 (Snapdragon 8 Elite) | v79 | Samsung Galaxy S25 Ultra | 22-26 s/step | 35-48 s/step (throttles when hot) |

Forecast in a Pocket is developed at [FBK](https://www.fbk.eu) (Fondazione Bruno Kessler, Trento) by Gabriele Franch.
Models: ECMWF [AIFS](https://github.com/ecmwf/anemoi-core) single-2.0 and ens-crps-2.0 (CC-BY-4.0).
