# Reference Data

This directory contains datapoints that can be used to identify changes in the
behavior of the app across versions, test integration of specific features and
measure the quality of the spot detection algorithm.

## Images

Reference images are provided in two format each, the `./images/png/` and
`./images/tiff/` directories. Each image represent sediment under UV light with
a given concentration of fluorescent tracing particles. The name of the file
indicates the density of tracer. Images named `C0.0.*` constitute the initial
concentration, with a dilution power of 0. Every time the dilution power
increases by 1, the tracer concentration is divided by 10. In general, for 
a given dilution power X, the image file will be named `CX.*` and the
concentration follows this formula:

```math
C_{tracer} = C_{ref} \cdot 10^{-X}
```

# Counting

The `./counts/` directory contains both manual and automated counts of tracer
particles for the reference images. Manual counting was done using
[Fiji](https://fiji.sc/), a distribution of the ImageJ image analysis software.
