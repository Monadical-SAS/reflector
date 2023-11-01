type PaginationProps = {
  page: number;
  setPage: (page: number) => void;
  total: number;
  size: number;
};

export default function Pagination(props: PaginationProps) {
  const { page, setPage, total, size } = props;
  const totalPages = Math.ceil(total / size);

  const pageNumbers = Array.from(
    { length: totalPages },
    (_, i) => i + 1,
  ).filter((pageNumber) => {
    if (totalPages <= 3) {
      // If there are 3 or fewer total pages, show all pages.
      return true;
    } else if (page <= 2) {
      // For the first two pages, show the first 3 pages.
      return pageNumber <= 3;
    } else if (page >= totalPages - 1) {
      // For the last two pages, show the last 3 pages.
      return pageNumber >= totalPages - 2;
    } else {
      // For all other cases, show 3 pages centered around the current page.
      return pageNumber >= page - 1 && pageNumber <= page + 1;
    }
  });

  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  return (
    <div className="flex justify-center space-x-4 my-4">
      <button
        className={`w-10 h-10 rounded-full p-2 border border-gray-300 rounded-full disabled:bg-white ${
          canGoPrevious ? "text-gray-500" : "text-gray-300"
        }`}
        onClick={() => handlePageChange(page - 1)}
        disabled={!canGoPrevious}
      >
        <i className="fa fa-chevron-left">&lt;</i>
      </button>

      {pageNumbers.map((pageNumber) => (
        <button
          key={pageNumber}
          className={`w-10 h-10 rounded-full p-2 border rounded-full ${
            page === pageNumber ? "border-gray-600" : "border-gray-300"
          } rounded`}
          onClick={() => handlePageChange(pageNumber)}
        >
          {pageNumber}
        </button>
      ))}

      <button
        className={`w-10 h-10 rounded-full p-2 border border-gray-300 rounded-full disabled:bg-white ${
          canGoNext ? "text-gray-500" : "text-gray-300"
        }`}
        onClick={() => handlePageChange(page + 1)}
        disabled={!canGoNext}
      >
        <i className="fa fa-chevron-right">&gt;</i>
      </button>
    </div>
  );
}
