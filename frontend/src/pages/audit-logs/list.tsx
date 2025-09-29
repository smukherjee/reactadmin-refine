import React from "react";
import {
  List,
  TextField,
  DateField,
  useTable,
} from "@refinedev/mui";
import { Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

export const AuditLogList = () => {
  const { tableQueryResult } = useTable({
    resource: "audit-logs",
  });

  const { data, isLoading } = tableQueryResult;

  return (
    <List>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>User ID</TableCell>
            <TableCell>Action</TableCell>
            <TableCell>Resource Type</TableCell>
            <TableCell>Resource ID</TableCell>
            <TableCell>Created At</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.data?.map((log) => (
            <TableRow key={log.id}>
              <TableCell>
                <TextField value={log.id} />
              </TableCell>
              <TableCell>
                <TextField value={log.user_id} />
              </TableCell>
              <TableCell>
                <TextField value={log.action} />
              </TableCell>
              <TableCell>
                <TextField value={log.resource_type} />
              </TableCell>
              <TableCell>
                <TextField value={log.resource_id} />
              </TableCell>
              <TableCell>
                <DateField value={log.created_at} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </List>
  );
};