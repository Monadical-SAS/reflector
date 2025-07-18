import React from "react";
import { Pagination, HStack } from "@chakra-ui/react";

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
      variant="ghost"
      size="sm"
    >
      <HStack>
        <Pagination.PrevTrigger />
        <Pagination.Context>
          {({ pages }) =>
            pages.map((pageItem, index) =>
              pageItem.type === "page" ? (
                <Pagination.Item key={index} {...pageItem} />
              ) : (
                <Pagination.Ellipsis key={index} index={index} />
              ),
            )
          }
        </Pagination.Context>
        <Pagination.NextTrigger />
      </HStack>
    </Pagination.Root>
  );
}
