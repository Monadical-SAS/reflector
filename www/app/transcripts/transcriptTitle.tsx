type TranscriptTitle = {
  title: string;
};

const TranscriptTitle = (props: TranscriptTitle) => {
  return (
    <h2 className="text-2xl lg:text-4xl font-extrabold text-center mb-4">
      {props.title}
    </h2>
  );
};

export default TranscriptTitle;
