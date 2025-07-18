import React from "react";
import { ButtonGroup, IconButton, Pagination } from "@chakra-ui/react";
import { FaChevronLeft, FaChevronRight } from "react-icons/fa6";

type PaginationProps = {
  page: number;
  setPage: (page: number) => void;
  total: number;
  size: number;
};

export default function PaginationComponent(props: PaginationProps) {
  const { page, setPage, total, size } = props;
  const totalPages = Math.ceil(total / size);

  if (totalPages <= 1) return null;

  return (
    <Pagination.Root
      count={total}
      pageSize={size}
      page={page}
      onPageChange={(details) => setPage(details.page)}
      siblingCount={2}
    >
      <ButtonGroup variant="ghost" size="sm">
        <Pagination.PrevTrigger asChild>
          <IconButton aria-label="Previous page" icon={<FaChevronLeft />} />
        </Pagination.PrevTrigger>

        <Pagination.Items>
          {({ items }) =>
            items.map((item, index) => {
              if (item.type === "page") {
                return (
                  <Pagination.Item key={index} {...item} asChild>
                    <IconButton
                      variant={item.value === page ? "solid" : "ghost"}
                      colorScheme={item.value === page ? "blue" : "gray"}
                      aria-label={`Page ${item.value}`}
                    >
                      {item.value}
                    </IconButton>
                  </Pagination.Item>
                );
              }

              if (item.type === "ellipsis") {
                return (
                  <Pagination.Ellipsis key={index} index={index} asChild>
                    <IconButton
                      variant="ghost"
                      isDisabled
                      pointerEvents="none"
                      aria-label="More pages"
                    >
                      ...
                    </IconButton>
                  </Pagination.Ellipsis>
                );
              }

              return null;
            })
          }
        </Pagination.Items>

        <Pagination.NextTrigger asChild>
          <IconButton aria-label="Next page" icon={<FaChevronRight />} />
        </Pagination.NextTrigger>
      </ButtonGroup>
    </Pagination.Root>
  );
}
