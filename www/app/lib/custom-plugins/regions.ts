// Source code: https://github.com/katspaugh/wavesurfer.js/blob/fa2bcfe/src/plugins/regions.ts

import RegionsPlugin, {
  RegionsPluginOptions,
} from "wavesurfer.js/dist/plugins/regions";

class CustomRegionsPlugin extends RegionsPlugin {
  public static create(options?: RegionsPluginOptions) {
    return new CustomRegionsPlugin(options);
  }

  constructor(options?: RegionsPluginOptions) {
    super(options);
    this["avoidOverlapping"] = () => {};
  }
}

export default CustomRegionsPlugin;
