import RegionsPlugin from "wavesurfer.js/dist/plugins/regions";

class CustomRegionsPlugin extends RegionsPlugin {
  static create(options) {
    return new CustomRegionsPlugin(options);
  }
  avoidOverlapping(region) {
    // Prevent overlapping regions
  }
}

export default CustomRegionsPlugin;
