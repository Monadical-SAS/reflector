import React, { useEffect } from "react";
import { Pagination, IconButton, ButtonGroup } from "@chakra-ui/react";
import { LuChevronLeft, LuChevronRight } from "react-icons/lu";

type PaginationProps = {
  page: number;
  setPage: (page: number) => void;
  total: number;
  size: number;
};

export const totalPages = (total: number, size: number) => {
  return Math.ceil(total / size);
};

export default function PaginationComponent(props: PaginationProps) {
  const { page, setPage, total, size } = props;
  useEffect(() => {
    if (page > totalPages(total, size)) {
      console.error(
        `Page number (${page}) is greater than total pages (${totalPages}) in pagination`,
      );
    }
  }, [page, totalPages(total, size)]);

  return (
    <Pagination.Root
      count={total}
      pageSize={size}
      page={page}
      onPageChange={(details) => setPage(details.page)}
      style={{ display: "flex", justifyContent: "center" }}
    >
      <ButtonGroup variant="ghost" size="xs">
        <Pagination.PrevTrigger asChild>
          <IconButton>
            <LuChevronLeft />
          </IconButton>
        </Pagination.PrevTrigger>
        <Pagination.Items
          render={(page) => (
            <IconButton variant={{ base: "ghost", _selected: "solid" }}>
              {page.value}
            </IconButton>
          )}
        />
        <Pagination.NextTrigger asChild>
          <IconButton>
            <LuChevronRight />
          </IconButton>
        </Pagination.NextTrigger>
      </ButtonGroup>
    </Pagination.Root>
  );
}
