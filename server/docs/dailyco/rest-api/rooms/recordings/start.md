# Source: https://docs.daily.co/reference/rest-api/rooms/recordings/start

#

POST

/rooms/:name/recordings/start

[Pay-as-you-go](https://www.daily.co/pricing)

Starts a recording with a given layout configuration.

Multiple recording sessions (up to `max_streaming_instances_per_room` on your Daily domain) can be started by specifying a unique `instanceId`. Each instance can have a different layout, participants, lifetime, and update rules.

A `503` status code may be returned if there are not enough workers available. In this case, you may retry the request again.

[Contact us](https://www.daily.co/contact/support) to configure `max_streaming_instances_per_room` for your domain.

You can pass configuration properties to this endpoint to control the look and feel of the recording, including the `type` of recording you would like to start. In order to start a `"raw-tracks"` recording, you must be using a [custom s3 bucket configuration](../../../../guides/products/live-streaming-recording/recording-calls-with-the-daily-api#raw-tracks).

The options currently include:

  * `height`, `width`: Can be specified to control the resolution of the live stream. The value must be even, i.e., a multiple of 2.

  * `backgroundColor`: Specifies the background color of the stream, formatted as `#rrggbb` or `#aarrggbb` string.

  * `fps`: Specifies the video frame rate per second.

  * `videoBitrate`: Specifies the video bitrate in kilobits per second (kbps) to use for video output. Value can range between `10` and `10000`. If not specified, the following bitrate values will be used for each given resolution:

    * `1080p`: `5000`
    * `720p`: `3000`
    * `480p`: `2000`
    * `360p`: `1000`
  * `audioBitrate`: Specifies the audio bitrate in kilobits per second (kbps) to use for audio output. Value can range between `10` and `320`.

  * `minIdleTimeOut`: Amount of time in seconds to wait before ending a recording or live stream when the room is idle (e.g. when all users have muted video and audio). Default: `300` (seconds). Note: Once the timeout has been reached, it typically takes an additional 1-3 minutes for the recording or live stream to be shut down.

  * `maxDuration`: maximum duration in seconds after which recording/streaming is forcefully stopped. Defaults: `10800` seconds (3 hours) for recordings, `86400` seconds (24 hours) for streaming. This is a preventive circuit breaker to prevent billing surprises in case a user starts recording/streaming and leaves the room.

  * `instanceId`: UUID for a streaming or recording session. Used when multiple streaming or recording sessions are running for single room. Default: `"c3df927c-f738-4471-a2b7-066fa7e95a6b"`. Note: `"c3df927c-f738-4471-a2b7-066fa7e95a6b"` is reserved internally; do not use this UUID.

  * `type`: specify type of recording ("cloud", "raw-tracks", "local") to start. Particular recording type must be enabled for the room or domain with enable_recording property.

  * `layout`: an object specifying the way participants’ videos are laid out in the live stream. A `preset` key with one of the following values must be provided:

    * `'default'`: This is the default grid layout, which renders participants in a grid, or in a vertical grid to the right, if a screen share is enabled. Optionally, a `max_cam_streams` integer key can be provided to specify how many cameras to include in the grid. The default value is 20, which is also the maximum number of cameras in a grid. The maximum may be increased at a later date.
    * `'audio-only'`: This layout creates an audio only cloud recording. Video will not be a part of the recording.
    * `'single-participant'`: Use this layout to limit the audio and video to be streamed to a specific participant. The selected participant’s session ID must be specified via a `session_id` key.
    * `'active-participant'`: This layout focuses on the current speaker, and places up to 9 other cameras to the right in a vertical grid in the order in which they last spoke.
    * `'portrait'`: Allows for mobile-friendly layouts. The video will be forced into portrait mode, where up to 2 participants will be shown. An additional `variant` key may be specified. Valid values are:
      * `'vertical'` for a vertical grid layout (the default)
      * `'inset'`for having one participant's video take up the entire screen, and the other inset in a smaller rectangle. Participants' videos are scaled and cropped to fit the entire available space. Participants with the `is_owner` flag are shown lower in the grid (vertical variant), or full screen (inset variant).
  * `'raw-tracks-audio-only'`: record only the audio tracks for raw-tracks recording. (NOTE: applicable only for raw-tracks recording)

    * `'custom'`: Allows for custom layouts. ([See below](/reference/daily-js/instance-methods/start-live-streaming#customize-your-video-layout).)



## Path params

`name`

string

The name of the room.

## Body params

`width`

number

Property that specifies the output width of the given stream.

`height`

number

Property that specifies the output height of the given stream.

`fps`

number

Property that specifies the video frame rate per second.

`videoBitrate`

number

Property that specifies the video bitrate for the output video in kilobits per second (kbps).

`audioBitrate`

number

Property that specifies the audio bitrate for the output audio in kilobits per second (kbps).

`minIdleTimeOut`

number

Amount of time in seconds to wait before ending a recording or live stream when the room is idle (e.g. when all users have muted video and audio). Default: 300 (seconds). Note: Once the timeout has been reached, it typically takes an additional 1-3 minutes for the recording or live stream to be shut down.

`maxDuration`

number

Maximum duration in seconds after which recording/streaming is forcefully stopped. Default: `15000` seconds (3 hours). This is a preventive circuit breaker to prevent billing surprises in case a user starts recording/streaming and leaves the room.

`backgroundColor`

string

Specifies the background color of the stream, formatted as #rrggbb or #aarrggbb string.

`instanceId`

string

UUID for a streaming or recording session. Used when multiple streaming or recording sessions are running for single room.

`type`

string

The type of recording that will be started.

Options: "cloud","raw-tracks"

Default: cloud

`layout`

object

An object specifying the way participants’ videos are laid out in the live stream. See given layout configs for description of fields. Preset must be defined.

### Default Layout

`preset`

string

Options: "default"

`max_cam_streams`

number

### Single Participant Layout

`preset`

string

Options: "single-participant"

`session_id`

string

### Active Participant Layout

`preset`

string

Options: "active-participant"

### Portrait Layout

`preset`

string

Options: "portrait"

`variant`

string

Options: "vertical","inset"

`max_cam_streams`

number

### Custom Layout

`preset`

string

Options: "custom"

`composition_id`

string

`composition_params`

object

`session_assets`

object

### Custom video layouts with VCS baseline composition

The baseline composition option is only available for cloud recordings and live streaming.

Daily offers a "baseline" composition option via the "custom" layout preset for customizing your video layouts while recording. This option allows for even more flexibility while using Daily's recording API.

Review our [Video Component System (VCS) guide](/guides/products/live-streaming-recording/vcs) or [VCS Simulator](https://daily.co/tools/vcs-simulator) for additional information and code examples.

Many VCS properties use a "grid unit". The grid unit is a designer-friendly, device-independent unit. The default grid size is 1/36 of the output's minimum dimension. In other words, 1gu = 20px on a 720p stream and 30px on a 1080p stream. Learn more about grid units in our [VCS SDK docs](/reference/vcs/layout-api#the-grid-unit).

### composition_params

###

`mode`

string

Sets the layout mode. Valid options:

  * **single** : Show a single full-screen video.
  * **split** : Show the first two participants side-by-side.
  * **grid** : Show up to 20 videos in a grid layout.
  * **dominant** : Show the active speaker in a large pane on the left, with additional video thumbnails on the right.
  * **pip** : Show the active speaker in a full-screen view, with the first participant inlaid in a corner.



Default: grid

`showTextOverlay`

boolean

Sets whether a text overlay is displayed. You can configure the contents of the overlay with the `text.*` properties.

Default: false

`showImageOverlay`

boolean

Sets whether an image overlay is displayed. You can configure the display of the overlay with the `image.*` properties. The image used must be passed in the `session_id` layout option when the stream or recording is _started_.

Default: false

`showBannerOverlay`

boolean

Sets whether a banner overlay is displayed. The banner can be used for TV-style "lower third" graphics, or displayed in any corner. You can configure the content of the overlay with the `banner.*` properties.

Default: false

`showWebFrameOverlay`

boolean

Sets whether a WebFrame overlay is displayed. You can configure the display of this live web browser overlay with the `webFrame.*` properties. The URL and the browser viewport size can be changed while your stream or recording is running.

Default: false

`showSidebar`

boolean

Sets whether a sidebar is displayed. You can configure the display of the sidebar with the `sidebar.*` properties.

Default: false

`showTitleSlate`

boolean

Sets whether a title screen (a "slate") is displayed. You can configure the display of the slate with the `titleSlate.*` properties.

Default: false

`enableAutoOpeningSlate`

boolean

Sets whether a title screen (a "slate") is automatically shown at the start of the stream. You can configure the display of this automatic slate with the `openingSlate.` properties.

Default: false

### Group: videoSettings

`videoSettings.maxCamStreams`

number

Limits the number of non-screenshare streams that are included in the output.

Default: 25

`videoSettings.preferredParticipantIds`

string

Lets you do render-time reordering of video inputs according to participant IDs within a Daily room. To enable this sorting, pass a comma-separated list of participant IDs as the value for this param; video inputs matching these IDs will be moved to the top of the list. If you pass an ID that is not present in the room, it's ignored. All other video inputs will remain in their original order. The default value is an empty string indicating no reordering. Also note that `videoSettings.preferScreenshare` takes precedence over the ordering passed here. For more information about how participants and videos are sorted, see the section on selecting participants.

Default:

`videoSettings.preferScreenshare`

boolean

When enabled, screen share inputs will be sorted before camera inputs. This is useful when prioritizing screen shares in your layout, especially when all inputs are not included in the final stream. For more information about how participants and videos are sorted, see the section on selecting participants.

Default: false

`videoSettings.omitPausedVideo`

boolean

When enabled, paused video inputs will not be included. By default this is off, and paused inputs are displayed with a placeholder graphic. ("Paused video" means that the video track for a participant is not available, either due to user action or network conditions.)

Default: false

`videoSettings.omitAudioOnly`

boolean

When enabled, audio-only inputs will not be included in rendering. By default this is off, and audio participants are displayed with a placeholder graphic.

Default: false

`videoSettings.omitExtraScreenshares`

boolean

When enabled, any screenshare video inputs beyond the first one will not be included in rendering. You can control the ordering of the inputs using the `layout.participants` property to explicitly select which participant should be first in the list of inputs.

Default: false

`videoSettings.showParticipantLabels`

boolean

Sets whether call participants' names are displayed on their video tiles.

Default: false

`videoSettings.roundedCorners`

boolean

Sets whether to display video tiles with squared or rounded corners. Note that some modes (`dominant` and `pip`) have additional params to control whether the main video has rounded corners or not.

Default: false

`videoSettings.cornerRadius_gu`

number

Sets the corner radius applied to video layers when `videoSettings.roundedCorners` is enabled, in grid units.

Default: 1.2

`videoSettings.scaleMode`

string

Controls how source video is displayed inside a tile if they have different aspect ratios. Use `'fill'` to crop the video to fill the entire tile. Use `'fit'` to make sure the entire video fits inside the tile, adding letterboxes or pillarboxes as necessary.

Default: fill

`videoSettings.scaleModeForScreenshare`

string

Controls how a screenshare video is displayed inside a tile if they have different aspect ratios. Use `'fill'` to crop the video to fill the entire tile. Use `'fit'` to make sure the entire video fits inside the tile, adding letterboxes or pillarboxes as necessary.

Default: fit

`videoSettings.placeholder.bgColor`

string

Sets the background color for video placeholder tile. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgb(0, 50, 80)

`videoSettings.highlight.color`

string

Sets the highlight color. It's used as the border color to indicate the 'dominant' video input (typically the active speaker). Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgb(255, 255, 255)

`videoSettings.highlight.stroke_gu`

number

Sets the stroke width used to render a highlight border. See also `'videoSettings.highlight.color'`. Specified in grid units.

Default: 0.2

`videoSettings.split.margin_gu`

number

Sets the visual margin between the two video layers shown in `split` mode, in grid units.

Default: 0

`videoSettings.split.direction`

string

Selects whether the `'split'` layout mode is rendered in a horizontal or vertical configuration. The default value `'auto-by-viewport'` means that the split direction will be automatically selected to be most appropriate for the current viewport size: if the viewport is landscape or square, the split axis is vertical; if portrait, the split axis is horizontal. Valid options: `'auto-by-viewport', 'vertical', 'horizontal'`

Default: auto-by-viewport

`videoSettings.split.scaleModeOverrides`

string

Overrides the scaleMode setting for the `split` layout mode. Both sides of the split can have separately defined scale modes. Pass a comma-separated list such as `fill, fit` (this would set the left-hand side video to `fill` and the right-hand side video to `fit`). See documentation for the `videoSettings.scaleMode` parameter for the valid options. Note that this setting also overrides `videoSettings.scaleModeForScreenshare`.

Default:

`videoSettings.grid.useDominantForSharing`

boolean

When enabled, the layout will automatically switch to `dominant` mode from `grid` if a screenshare video input is available. By using this automatic behavior, you avoid having to manually switch the mode via an API call.

Default: false

`videoSettings.grid.itemInterval_gu`

number

Overrides the visual margin between items in `grid` mode, in grid units. The default value of -1 means that the layout algorithm selects a reasonable margin automatically depending on the number of videos.

Default: -1

`videoSettings.grid.outerPadding_gu`

number

Overrides the outer padding around items in `grid` mode, in grid units. The default value of -1 means that the layout algorithm selects a reasonable padding automatically depending on the number of videos.

Default: -1

`videoSettings.grid.highlightDominant`

boolean

By default, the `grid` mode will highlight the dominant video (typically the "active speaker") with a light outline. You can disable the highlight using this setting.

Default: true

`videoSettings.grid.preserveAspectRatio`

boolean

By default, the layout for the `grid` mode will try to preserve the aspect ratio of the input videos, i.e. avoid cropping the videos and instead add margins around the grid if needed. Setting this parameter to `false` will make the grid layout fill all available area, potentially cropping the videos.

Default: true

`videoSettings.dominant.position`

string

Control where the dominant (or "active speaker") video is displayed in the `dominant` layout mode. Values are `left`, `right`, `top` or `bottom`.

Default: left

`videoSettings.dominant.splitPos`

number

Sets the position of the imaginary line separating the dominant video from the smaller tiles when using the `dominant` layout. Values are from 0 to 1. The default is 0.8, so if `videoSettings.dominant.position` is set to `left`, the dominant video will take 80% of the width of the screen on the left.

Default: 0.8

`videoSettings.dominant.numChiclets`

number

Controls how many "chiclets", or smaller video tiles, appear alongside the dominant video when using the `dominant` layout.

Default: 5

`videoSettings.dominant.followDomFlag`

boolean

When in `dominant` mode, the large tile displays the active speaker by default. Turn off this `followDomFlag` to display the first participant instead of the active speaker.

Default: true

`videoSettings.dominant.itemInterval_gu`

number

Margin between the “chiclet” items, in grid units.

Default: 0.7

`videoSettings.dominant.outerPadding_gu`

number

Padding around the row/column of “chiclet” items, in grid units.

Default: 0.5

`videoSettings.dominant.splitMargin_gu`

number

Margin between the "dominant" video and the row/column of "chiclet" items, in grid units.

Default: 0

`videoSettings.dominant.sharpCornersOnMain`

boolean

Sets whether the "dominant" video will be rendered with rounded corners when `videoSettings.roundedCorners` is enabled. Defaults to false because sharp corners are a more natural choice for the default configuration where the dominant video is tightly aligned to viewport edges.

Default: true

`videoSettings.pip.position`

string

Sets the position of the smaller video in the `pip` (picture-in-picture) layout. Valid options: `'top-left'`, `'top-right'`, `'bottom-left'`, `'bottom-right'`.

Default: top-right

`videoSettings.pip.aspectRatio`

number

Sets the aspect ratio of the smaller video in the `pip` layout. The default is 1.0, which produces a square video.

Default: 1

`videoSettings.pip.height_gu`

number

Sets the height of the smaller video in the `pip` layout, measured in grid units.

Default: 12

`videoSettings.pip.margin_gu`

number

Sets the margin between the smaller video and the edge of the frame in the `pip` layout, in grid units.

Default: 1.5

`videoSettings.pip.followDomFlag`

boolean

When in "pip" (or picture-in-picture) mode, the overlay tile displays the first participant in the participant array by default. Turn on this `followDomFlag` to display the active speaker instead.

Default: false

`videoSettings.pip.sharpCornersOnMain`

boolean

Sets whether the main video in `pip` mode will be rendered with rounded corners when `videoSettings.roundedCorners` is enabled. Defaults to false because sharp corners are a more natural choice for the default configuration where the main video is full-screen (no margin to viewport edges).

Default: true

`videoSettings.labels.fontFamily`

string

Sets the participant label style option: font family. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Bitter`, `Exo`, `Magra`, `SuezOne`, `Teko`

Default: Roboto

`videoSettings.labels.fontWeight`

string

Sets the participant label text font weight. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 600

`videoSettings.labels.fontSize_pct`

number

Sets the participant label text font size.

Default: 100

`videoSettings.labels.offset_x_gu`

number

Sets the offset value for participant labels on the x-axis, measured in grid units.

Default: 0

`videoSettings.labels.offset_y_gu`

number

Sets the offset value for participant labels on the y-axis, measured in grid units.

Default: 0

`videoSettings.labels.color`

string

Sets the participant label font color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: white

`videoSettings.labels.strokeColor`

string

Sets the label font stroke color (the line outlining the text letters). Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 0, 0.9)

`videoSettings.margin.left_gu`

number

Sets the left margin value applied to videos (in any layout mode), in grid units. You can use these `videoSettings.margin.*` params to shrink the video area, for example to make room for overlays.

Default: 0

`videoSettings.margin.right_gu`

number

Sets the right margin value applied to videos (in any layout mode), in grid units. You can use these `videoSettings.margin.*` params to shrink the video area, for example to make room for overlays.

Default: 0

`videoSettings.margin.top_gu`

number

Sets the top margin value applied to videos (in any layout mode), in grid units. You can use these `videoSettings.margin.*` params to shrink the video area, for example to make room for overlays.

Default: 0

`videoSettings.margin.bottom_gu`

number

Sets the bottom margin value applied to videos (in any layout mode), in grid units. You can use these `videoSettings.margin.*` params to shrink the video area, for example to make room for overlays.

Default: 0

### Group: text

`text.content`

string

Sets the string to be displayed if `showTextOverlay` is true.

Default:

`text.source`

string

Sets the data source used for the text displayed in the overlay. The default value 'param' means that the value of param `text.content` is used. Valid options: `param`, `highlightLines.items`, `chatMessages`, `transcript`

Default: param

`text.align_horizontal`

string

Sets the horizontal alignment of the text overlay within the video frame. Values are `left`, `right`, or `center`.

Default: center

`text.align_vertical`

string

Sets the vertical alignment of the text overlay within the video frame. Values are `top`, `bottom`, or `center`.

Default: center

`text.offset_x_gu`

number

Sets an x-offset (horizontal) to be applied to the text overlay's position based on the values of `text.align_horizontal` and `text.align_vertical`.

Default: 0

`text.offset_y_gu`

number

Sets a y-offset (vertical) to be applied to the text overlay's position based on the values of `text.align_horizontal` and `text.align_vertical`.

Default: 0

`text.rotation_deg`

number

Applies a rotation to the text overlay. Units are degrees, and positive is a clockwise rotation.

Default: 0

`text.fontFamily`

string

Sets the font of the text overlay. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Anton`, `Bangers`, `Bitter`, `Exo`, `Magra`, `PermanentMarker`, `SuezOne`, `Teko`

Default: DMSans

`text.fontWeight`

string

Selects a weight variant from the selected font family. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 500

`text.fontStyle`

string

Sets the font style for text. Valid options: 'normal','italic'.

Default:

`text.fontSize_gu`

number

Sets the text overlay font size using grid units (gu). By default, one grid unit is 1/36 of the smaller dimension of the viewport (e.g. 20px in a 1280*720 stream).

Default: 2.5

`text.color`

string

Sets the color and transparency of the text overlay. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(255, 250, 200, 0.95)

`text.strokeColor`

string

Sets the color of the stroke drawn around the characters in the text overlay. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 0, 0.8)

`text.stroke_gu`

number

Sets the width of the stroke drawn around the characters in the text overlay. Specified in grid units.

Default: 0.5

`text.highlight.color`

text

Sets the color and transparency of a highlighted item in the text overlay. To display a highlight, the value of param `text.source` must be set to `highlightLines.items`. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(255, 255, 0, 1)

`text.highlight.fontWeight`

enum

Sets the font weight of a highlighted item in the text overlay. To display a highlight, the value of param `text.source` must be set to `highlightLines.items`.

Default: 700

### Group: image

`image.assetName`

string

Sets the overlay image. Icon asset must be included in `session_assets` object. `showImageOverlay` must be `true`.

Default: overlay.png

`image.emoji`

text

Sets an emoji to be rendered instead of an image asset. If this string is non-empty, it will override the value of `image.assetName`. The string value must be an emoji.

Default:

`image.position`

string

Sets position of overlay image. Valid options: `'top-left'`, `'top-right'`, `'bottom-left'`, `'bottom-right'`

Default: top-right

`image.fullScreen`

boolean

Sets overlay image to full screen.

Default: false

`image.aspectRatio`

number

Sets aspect ratio of overlay image.

Default: 1.778

`image.height_gu`

number

Sets height of overlay image, in grid units.

Default: 12

`image.margin_gu`

number

Sets margin between the overlay image and the viewport edge, in grid units.

Default: 1.5

`image.opacity`

number

Sets opacity of overlay image, in range 0-1. Default value of 1 is full opacity.

Default: 1

`image.enableFade`

boolean

Sets the overlay image to fade in or out when the `showImageOverlay` property is updated.

Default: true

### Group: webFrame

`webFrame.url`

string

Sets the web page URL to be loaded into the WebFrame overlay's embedded browser.

Default:

`webFrame.viewportWidth_px`

number

Sets the width of the embedded browser window used to render the WebFrame overlay.

Default: 1280

`webFrame.viewportHeight_px`

number

Sets the height of the embedded browser window used to render the WebFrame overlay.

Default: 720

`webFrame.position`

string

Sets position of the WebFrame overlay. Valid options: `'top-left'`, `'top-right'`, `'bottom-left'`, `'bottom-right'`

Default: top-right

`webFrame.fullScreen`

boolean

Sets the WebFrame overlay to full screen.

Default: false

`webFrame.height_gu`

number

Sets height of the WebFrame overlay, in grid units.

Default: 12

`webFrame.margin_gu`

number

Sets margin between the WebFrame overlay and the viewport edge, in grid units.

Default: 1.5

`webFrame.opacity`

number

Sets opacity of the WebFrame overlay, in range 0-1. Default value of `1` is full opacity.

Default: 1

`webFrame.enableFade`

boolean

Sets the WebFrame overlay to fade in or out when the `showWebFrameOverlay` property is updated.

Default: true

`webFrame.keyPress.keyName`

string

Sets the keyboard key to be sent to the WebFrame browser in a simulated key press. Valid options:

  * Digits **0 - 9**
  * Letters **A - Z**
  * ASCII special characters, e.g. **!** , **@** , **+** , **>** , etc.
  * Function keys **F1 - F12**
  * **Enter**
  * **Escape**
  * **Backspace**
  * **Tab**
  * Arrow keys **ArrowUp, ArrowDown, ArrowLeft, ArrowRight**
  * **PageDown, PageUp**



Default: ArrowRight

`webFrame.keyPress.modifiers`

string

Sets keyboard modifier keys to be sent to the WebFrame browser in a simulated key press. Valid options: `"Shift"`, `"Control"`, `"Alt"`, `"Meta"` (on a Mac keyboard, Alt is equal to Option and Meta is equal to Command).

Default:

`webFrame.keyPress.key`

number

Triggers a simulated key press to be sent to WebFrame. To send a key press, increment the value of `key`. (Note the difference between this and `keyName` which is the simulated key to be sent.)

Default: 0

### Group: banner

`banner.title`

text

Sets the title text displayed in the banner component.

Default: Hello world

`banner.subtitle`

text

Sets the subtitle text displayed in the banner component.

Default: This is an example subtitle

`banner.source`

string

Sets the data source for the text displayed in the banner component. Valid options: `param`, `highlightLines.items`, `chatMessages`, `transcript`

Default: param

`banner.position`

string

Sets position of the banner component. Valid options: `'top-left'`, `'top-right'`, `'bottom-left'`, `'bottom-right'`

`banner.enableTransition`

boolean

Sets the banner to fade in or out when the `showBannerOverlay` property is updated.

Default: true

`banner.margin_x_gu`

number

Horizontal margin, specified in grid units.

Default: 0

`banner.margin_y_gu`

number

Vertical margin, specified in grid units.

Default: 1

`banner.padding_gu`

number

Padding inside the component, specified in grid units.

Default: 2

`banner.alwaysUseMaxW`

boolean

Sets whether the banner component will always use its maximum width (specified using `banner.maxW_pct_default` and `banner.maxW_pct_portrait`). If false, the banner component will shrink horizontally to fit text inside it, if appropriate.

Default: false

`banner.maxW_pct_default`

number

Sets the maximum width for the banner component, as a percentage of the viewport size.

Default: 65

`banner.maxW_pct_portrait`

number

Sets the maximum width for the banner component, as a percentage of the viewport size, applied only when the viewport aspect ratio is portrait (i.e. smaller than 1). This override is useful because on a narrow screen the banner display typically needs more horizontal space than on a landscape screen.

Default: 90

`banner.rotation_deg`

number

Applies a rotation to the banner component. Units are degrees, and positive is a clockwise rotation.

Default: 0

`banner.cornerRadius_gu`

number

Sets the corner radius of the banner component outline. Specified in grid units.

Default: 0

`banner.showIcon`

boolean

Sets whether an icon is displayed in the banner component (`true` or `false`).

Default: true

`banner.icon.assetName`

text

Sets image asset value for the banner icon. Icon asset must be included in `session_assets` object.

Default:

`banner.icon.emoji`

text

Sets an emoji to be rendered as the banner icon. If this string is non-empty, it will override `banner.icon.assetName`. The string value must be an emoji.

Default: 🎉

`banner.icon.size_gu`

number

Sets the size of the banner icon, specified in grid units.

Default: 3

`banner.color`

text

Sets the banner component's background color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(50, 60, 200, 0.9)

`banner.strokeColor`

text

Sets the color of the outline drawn around the banner component. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 30, 0.44)

`banner.stroke_gu`

number

Sets the width of the stroke drawn around the banner component. Specified in grid units.

Default: 0

`banner.text.color`

text

Sets the banner component's text color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: white

`banner.text.strokeColor`

text

Sets the color of the stroke drawn around the characters in the banner component. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 0, 0.1)

`banner.text.stroke_gu`

number

Sets the width of the stroke drawn around the characters in the banner component. Specified in grid units.

Default: 0.5

`banner.text.fontFamily`

string

Sets the font of text displayed in the banner component. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Anton`, `Bangers`, `Bitter`, `Exo`, `Magra`, `PermanentMarker`, `SuezOne`, `Teko`

Default: Roboto

`banner.title.fontSize_gu`

number

Sets the banner title font size using grid units (gu). By default, one grid unit is 1/36 of the smaller dimension of the viewport (e.g. 20px in a 1280*720 stream).

Default: 2

`banner.title.fontWeight`

string

Sets the banner title font weight. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 500

`banner.title.fontStyle`

string

Sets the font style for the banner title. Valid options: 'normal','italic'.

Default:

`banner.subtitle.fontSize_gu`

number

Sets the banner subtitle font size using grid units (gu). By default, one grid unit is 1/36 of the smaller dimension of the viewport (e.g. 20px in a 1280*720 stream).

Default: 1.5

`banner.subtitle.fontWeight`

string

Sets the banner subtitle font weight. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 300

`banner.subtitle.fontStyle`

string

Sets the font style for the banner subtitle. Valid options: 'normal','italic'.

Default:

### Group: toast

`toast.key`

number

Triggers display of toast component. To send a toast, increment the value of `key`

Default: 0

`toast.text`

string

Sets text displayed in toast component.

Default: Hello world

`toast.source`

string

Sets the data source used for the text displayed in the toast component. The default value `param` means that the value of param `toast.content` is used. Valid options: `param`, `chatMessages`, `transcript`

Default: param

`toast.duration_secs`

number

Sets duration of time toast component is displayed (in seconds).

Default: 4

`toast.maxW_pct_default`

number

Sets the maximum width for the toast component, as a percentage of the viewport size.

Default: 50

`toast.maxW_pct_portrait`

number

Sets the maximum width for the toast component, as a percentage of the viewport size, applied only when the viewport aspect ratio is portrait (i.e. smaller than 1). This override is useful because on a narrow screen the toast display typically needs more horizontal space than on a landscape screen.

Default: 80

`toast.showIcon`

boolean

Sets whether icon is displayed in toast component (`true` or `false`).

Default: true

`toast.icon.assetName`

string

Sets asset value for toast icon. Icon asset must be included in `session_assets` object.

Default:

`toast.icon.emoji`

text

Sets an emoji to be rendered as the toast icon. If this string is non-empty, it will override `toast.icon.assetName`. The string value must be an emoji.

Default: 🎉

`toast.icon.size_gu`

number

Sets the size of the toast icon, in grid units.

Default: 3

`toast.color`

string

Sets the toast component's background color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(15, 50, 110, 0.6)

`toast.strokeColor`

string

Sets the color of the stroke drawn around the text characters in the toast component. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 30, 0.44)

`toast.text.color`

string

Sets the toast component's text color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: white

`toast.text.fontFamily`

string

Sets the toast component's font family. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Bitter`, `Exo`, `Magra`, `SuezOne`, `Teko`

Default: Roboto

`toast.text.fontWeight`

number

Sets the font weight for the toast component's text. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 500

`toast.text.fontSize_pct`

number

Sets the font size for the toast component's text.

Default: 100

### Group: openingSlate

`openingSlate.duration_secs`

number

Sets the number of seconds that the opening slate will be displayed when the stream starts. After this time, the slate goes away with a fade-out effect.

Default: 4

`openingSlate.title`

string

Sets text displayed in the main title of the opening slate.

Default: Welcome

`openingSlate.subtitle`

string

Sets text displayed in the subtitle (second line) of the opening slate.

Default:

`openingSlate.bgImageAssetName`

string

Sets an image to be used as the background for the slate. This image asset must be included in `session_assets` object when starting the stream/recording.

Default:

`openingSlate.bgColor`

string

Sets the slate's background color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 0, 1)

`openingSlate.textColor`

string

Sets the text color of the titles in the slate. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(255, 255, 255, 1)

`openingSlate.fontFamily`

string

Sets the font of the titles in the slate. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Anton`, `Bangers`, `Bitter`, `Exo`, `Magra`, `PermanentMarker`, `SuezOne`, `Teko`

Default: Bitter

`openingSlate.fontWeight`

string

Selects a weight variant from the selected font family. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 500

`openingSlate.fontStyle`

string

Sets the font style for the titles in the slate. Valid options: 'normal','italic'.

Default:

`openingSlate.fontSize_gu`

number

Sets the main title font size using grid units (gu). By default, one grid unit is 1/36 of the smaller dimension of the viewport (e.g. 20px in a 1280*720 stream).

Default: 2.5

`openingSlate.subtitle.fontSize_pct`

number

Sets the subtitle font size as a percentage of the main title.

Default: 75

`openingSlate.subtitle.fontWeight`

string

Selects a weight variant from the selected font family specifically for the subtitle. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 400

### Group: titleSlate

`titleSlate.enableTransition`

boolean

Sets the slate to fade in or out when the `showTitleSlate` property is updated.'

Default: true

`titleSlate.title`

string

Sets text displayed in the main title of the slate.

Default: Title slate

`titleSlate.subtitle`

string

Sets text displayed in the subtitle (second line) of the slate.

Default: Subtitle

`titleSlate.bgImageAssetName`

string

Sets an image to be used as the background for the slate. This image asset must be included in `session_assets` object when starting the stream/recording.

Default:

`titleSlate.bgColor`

string

Sets the slate's background color. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 0, 1)

`titleSlate.textColor`

string

Sets the text color of the titles in the slate. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(255, 255, 255, 1)

`titleSlate.fontFamily`

string

Sets the font of the titles in the slate. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Anton`, `Bangers`, `Bitter`, `Exo`, `Magra`, `PermanentMarker`, `SuezOne`, `Teko`

Default: Bitter

`titleSlate.fontWeight`

string

Selects a weight variant from the selected font family. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 500

`titleSlate.fontStyle`

string

Sets the font style for the titles in the slate. Valid options: 'normal','italic'.

Default:

`titleSlate.fontSize_gu`

number

Sets the main title font size using grid units (gu). By default, one grid unit is 1/36 of the smaller dimension of the viewport (e.g. 20px in a 1280*720 stream).

Default: 2.5

`titleSlate.subtitle.fontSize_pct`

number

Sets the subtitle font size as a percentage of the main title.

Default: 75

`titleSlate.subtitle.fontWeight`

string

Selects a weight variant from the selected font family specifically for the subtitle. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 400

### Group: sidebar

`sidebar.shrinkVideoLayout`

boolean

Sets whether the sidebar is displayed on top of video elements. If set to `true` , the video layout is shrunk horizontally to make room for the sidebar so they don't overlap.

Default: false

`sidebar.source`

string

Sets the data source for the text displayed in the sidebar. Valid options: `param`, `highlightLines.items`, `chatMessages`, `transcript`

Default: highlightLines.items

`sidebar.padding_gu`

number

Padding inside the sidebar, specified in grid units.

Default: 1.5

`sidebar.width_pct_landscape`

number

Sets the width of the sidebar, as a percentage of the viewport size, applied when the viewport is landscape (its aspect ratio is greater than 1).

Default: 30

`sidebar.height_pct_portrait`

number

Sets the width of the sidebar, as a percentage of the viewport size, applied when the viewport is portrait or square (its aspect ratio is less than or equal to 1).

Default: 25

`sidebar.bgColor`

text

Sets the sidebar's background color and opacity. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(0, 0, 50, 0.55)

`sidebar.textColor`

text

Sets the sidebar's text color and opacity. Valid options:

  * Hex color codes

  * RGB or RGBA syntax

  * Standard CSS color names (e.g. 'blue')




Default: rgba(255, 255, 255, 0.94)

`sidebar.fontFamily`

string

Sets the font of text displayed in the sidebar. Valid options: `DMSans`, `Roboto`, `RobotoCondensed`, `Anton`, `Bangers`, `Bitter`, `Exo`, `Magra`, `PermanentMarker`, `SuezOne`, `Teko`

Default: DMSans

`sidebar.fontWeight`

string

Sets the sidebar text font weight. Valid options: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900`.

Note: Not all font weights are valid for every font family.

Default: 300

`sidebar.fontStyle`

string

Sets the font style for text in the sidebar. Valid options: 'normal','italic'.

Default:

`sidebar.fontSize_gu`

number

Sets the sidebar text font size using grid units (gu). By default, one grid unit is 1/36 of the smaller dimension of the viewport (e.g. 20px in a 1280*720 stream).

Default: 1.4

`sidebar.textHighlight.color`

text

Sets the color used for the highlighted item in the sidebar.

Default: rgba(255, 230, 0, 1)

`sidebar.textHighlight.fontWeight`

string

Sets the font weight used for the highlighted item in the sidebar.

Default: 600

### Group: highlightLines

`highlightLines.items`

text

Sets a list of text items. Items must be separated by newline characters. This param is a data source that can be displayed in other components like TextOverlay, Banner and Sidebar using the various "source" params available in the settings for those components.

`highlightLines.position`

number

Sets the highlight index associated with the text items specified in `highlightLines.items`. The item at this index will be displayed using a special highlight style (which depends on the component used to display this data). If you don't want a highlight, set this value to -1.

Default: 0

### Group: emojiReactions

`emojiReactions.source`

string

Sets the data source used for emoji reactions. The default value `emojiReactions` means that this component will display emojis that are sent via the standard source API.

The other valid option is `param`, which lets you send a reaction using param values instead of the standard source. The steps are as follows: set `emojiReactions.source` to `param`, set a single-emoji string for `emojiReactions.emoji`, and increment the value of `emojiReactions.key` to send one emoji for display.

Default: emojiReactions

`emojiReactions.key`

number

If `emojiReactions.source` is set to `param`, increment this numeric key to send a new emoji for display.

Default: 0

`emojiReactions.emoji`

text

If `emojiReactions.source` is set to `param`, set a single emoji as the string value for this param, and it will be the next emoji reaction rendered when `emojiReactions.key` is incremented.

Default:

`emojiReactions.offset_x_gu`

number

Sets a horizontal offset applied to the emoji reactions animation rendering (each new emoji floats up from the bottom of the screen). Specified in grid units.

Default: 0

### Group: debug

`debug.showRoomState`

boolean

When set to true, a room state debugging display is visible. It prints various information about participant state.

Default: false

`debug.overlayOpacity`

number

Sets the opacity of the debugging display which can be toggled using `debug.showRoomState`.

Default: 90

## Selecting participants

The baseline composition has several modes that display multiple participant videos. You may be wondering how to control which participants appear in specific places within those layouts.

Internally, VCS uses an ordered array of video inputs that it calls ["video input slots"](/reference/vcs/components/video). By default, that array will contain all participants in the order in which they joined the call. But there are two ways you can override this default behavior and choose which participants appear in your layout:

  1. Participant selection on the **room level** using the `participants` property.
  2. Input reordering on the **composition level** (a.k.a. switching) using the `preferredParticipantIds` and `preferScreenshare` params available in the baseline composition.



These two are not mutually exclusive. What's the difference, and when should you use one or the other?

**Room-level participant selection** is a powerful generic tool. It lets you choose any participants within the room, and will trigger any necessary backend connections so that a participant's audio and video streams become available to the VCS rendering server. This means there may be a slight delay as connections are made.

In contrast, **composition-level input reordering** (a.k.a. switching) happens at the very last moment in the VCS engine just before a video frame is rendered. (The name "switching" refers to a video switcher, a hardware device used in traditional video production for this kind of input control.) It's applied together with any other composition param updates you're sending, so there is a guarantee of synchronization. You should use this method when you want to ensure that the reordering of inputs happens precisely at the same time as your update to some other composition param value(s). For example, if you're switching a layout mode and want the inputs to be sorted in a different way simultaneously.

You can use the two methods together. Room-level selection using the `participants` property lets you establish the participants whose streams will be available to the rendering. You can then do rapid switching within that selection using the `preferredParticipantIds` and `preferScreenshare` params in the baseline composition.

Here's an example of selecting three specific participant video tracks, everyone's audio tracks, and sorting the video by most recent active speaker:

Copy to clipboard

Here's another example where we're further sorting the same video tracks using the baseline composition params. The params update is switching to a different layout mode (`'split'`). This mode can only show two participants, so we use `videoSettings.preferredParticipantIds` to select the two participants in a clean frame-synchronized way, without having to modify the underlying connections made via the `participants` property:

Copy to clipboard

**If you include the`participants` object in a `startLiveStreaming()`/`startRecording()` or `updateLiveStreaming()`/`updateRecording()` call, you need to include it in any subsequent `updateLiveStreaming()`/`updateRecording()` calls as well, even if you aren't changing it.**

If you set the `participants` property for your recording or live stream and then make an `updateLiveStreaming()`/`updateRecording()` call to update the `composition_params`, you'll need to resend the same values you used before in the `participants` property. This is true even if you are not updating the `participants` property. If you don't, the participant configuration will reset to default, as if you hadn't set it in the first place —meaning VCS will receive all audio and video tracks from all participants, sorted by the order in which the participants joined the call.

### `participants` properties

`video`

array

Required. An array of strings indicating which participant videos to make available to VCS. Possible values are:

  * `["participant-guid-1", "participant-guid-2", "participant-guid-3"]`: A list of specific participant IDs

  * `["*"]`: everyone

  * `["owners"]`: All call owners




`audio`

array

An optional array of strings indicating which participant audio tracks to make available to VCS. Possible values are the same as the `video` property.

`sort`

string

The only currently valid value for this property is `"active"`. This property controls the order in which VCS sees the participant video tracks. When set to `"active"`, each time the call's active speaker changes to a different participant, that participant will bubble up to the first position in the array. In other words, setting sort to `"active"` will cause an n-tile layout to always show the n most recent speakers in the call. If you leave the property unset, the list of participants will stay in a fixed order: either the order you specified in the `video` property, or in the order they joined the call if you use `"*"` or `"owners"`.

## Session assets

Session assets — images or custom VCS components — that can be passed as assets and used during a live stream or cloud recording. To learn more, visit our [Session assets page](/reference/vcs/session-assets) in the VCS SDK reference docs.

**Note** : Session assets must be made available at the beginning of the recording or live stream even if they are not used until later in the call.

## Example requests

**Default**

**Single Participant**

**Active Participant**

**Portrait**

**Custom**

**200 OK**

**400 bad request**

Copy to clipboard

* * *

Previous

[Next](/reference/rest-api/rooms/recordings/update)
