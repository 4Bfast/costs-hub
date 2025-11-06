import { FileX, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: 'file' | 'search' | 'plus';
  showAction?: boolean;
}

export function EmptyState({
  title = "No data found",
  message = "There's no data to display at the moment.",
  actionLabel = "Add Data",
  onAction,
  icon = 'file',
  showAction = false
}: EmptyStateProps) {
  const IconComponent = {
    file: FileX,
    search: Search,
    plus: Plus
  }[icon];

  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <IconComponent className="h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6 max-w-md">{message}</p>
        
        {showAction && onAction && (
          <Button onClick={onAction}>
            <Plus className="w-4 h-4 mr-2" />
            {actionLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
