import { Button, Flex, IconButton } from "@chakra-ui/react";
import { FaChevronLeft, FaChevronRight } from "react-icons/fa";

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
    <Flex justify="center" align="center" gap="2" mx="2">
      <IconButton
        isRound={true}
        variant="text"
        color={!canGoPrevious ? "gray" : "dark"}
        mb="1"
        icon={<FaChevronLeft />}
        onClick={() => handlePageChange(page - 1)}
        disabled={!canGoPrevious}
        aria-label="Previous page"
      />

      {pageNumbers.map((pageNumber) => (
        <Button
          key={pageNumber}
          variant="text"
          color={page === pageNumber ? "gray" : "dark"}
          onClick={() => handlePageChange(pageNumber)}
          disabled={page === pageNumber}
        >
          {pageNumber}
        </Button>
      ))}

      <IconButton
        isRound={true}
        variant="text"
        color={!canGoNext ? "gray" : "dark"}
        icon={<FaChevronRight />}
        mb="1"
        onClick={() => handlePageChange(page + 1)}
        disabled={!canGoNext}
        aria-label="Next page"
      />
    </Flex>
  );
}
