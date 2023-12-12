export default ({ playing }) => (
  <div className="flex justify-between w-16 h-8 m-auto">
    <div
      className={`bg-blue-400 rounded w-2 ${
        playing ? "animate-wave-quiet" : ""
      }`}
    ></div>
    <div
      className={`bg-blue-400 rounded w-2 ${
        playing ? "animate-wave-normal" : ""
      }`}
    ></div>
    <div
      className={`bg-blue-400 rounded w-2 ${
        playing ? "animate-wave-quiet" : ""
      }`}
    ></div>
    <div
      className={`bg-blue-400 rounded w-2 ${
        playing ? "animate-wave-loud" : ""
      }`}
    ></div>
    <div
      className={`bg-blue-400 rounded w-2 ${
        playing ? "animate-wave-normal" : ""
      }`}
    ></div>
  </div>
);
