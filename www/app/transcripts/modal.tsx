type ModalProps = {
  title: string;
  text: string;
};

export default function Modal(props: ModalProps) {
  return (
    <>
      <div className="w-full flex flex-col items-center justify-center bg-white px-6 py-8 mt-8 rounded-xl">
        <h1 className="text-2xl font-bold text-blue-500">{props.title}</h1>
        <p className="text-gray-500 text-center mt-5">{props.text}</p>
      </div>
    </>
  );
}
