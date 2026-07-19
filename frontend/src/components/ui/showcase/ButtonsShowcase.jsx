import React from 'react';
import Button from '../Button';
import IconButton from '../IconButton';
import ButtonGroup from '../ButtonGroup';

export const ButtonsShowcase = () => {
  return (
    <div className="showcase-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 className="text-h3" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Buttons</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">Variants</h4>
        <ButtonGroup>
          <Button variant="primary">Primary Action</Button>
          <Button variant="secondary">Secondary Action</Button>
          <Button variant="danger">Danger Action</Button>
          <Button variant="outline">Outline Action</Button>
          <Button variant="ghost">Ghost Action</Button>
        </ButtonGroup>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">States</h4>
        <ButtonGroup>
          <Button variant="primary" disabled>Disabled State</Button>
          <Button variant="primary" loading>Loading State</Button>
        </ButtonGroup>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 className="text-h4">Icon Buttons</h4>
        <div style={{ display: 'flex', gap: '12px' }}>
          <IconButton
            icon={<span>🔍</span>}
            ariaLabel="Search"
            variant="primary"
          />
          <IconButton
            icon={<span>⚙️</span>}
            ariaLabel="Settings"
            variant="secondary"
          />
          <IconButton
            icon={<span>⚠️</span>}
            ariaLabel="Delete"
            variant="danger"
          />
        </div>
      </div>
    </div>
  );
};
export default ButtonsShowcase;
